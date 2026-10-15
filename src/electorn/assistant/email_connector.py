"""Gmail Integration using official Google OAuth 2.0 and Gmail REST API."""

from __future__ import annotations

import base64
import email
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import httpx

from electorn.assistant.schema import AttachmentMetadata, ChannelType, MessageRecord

logger = logging.getLogger(__name__)

# Scopes: Default to readonly, elevate to send only when explicitly permitted
GMAIL_READONLY_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"
GMAIL_SEND_SCOPE = "https://www.googleapis.com/auth/gmail.send"


class GmailConnector:
    """Official Gmail OAuth 2.0 and API integration."""

    def __init__(self, token_path: Optional[Path] = None, credentials_path: Optional[Path] = None) -> None:
        self.base_dir = token_path.parent if token_path else (Path.home() / ".electorn" / "assistant" / "auth")
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.token_file = token_path or (self.base_dir / "gmail_token.json")
        self.credentials_file = credentials_path or (self.base_dir / "gmail_credentials.json")
        self._access_token: Optional[str] = None
        self._load_token()

    def _load_token(self) -> None:
        if self.token_file.exists():
            try:
                data = json.loads(self.token_file.read_text(encoding="utf-8"))
                self._access_token = data.get("access_token")
            except Exception:
                self._access_token = None

    def is_connected(self) -> bool:
        """Check if a valid token is stored."""
        return bool(self._access_token)

    def get_auth_url(self, client_id: str, redirect_uri: str = "http://localhost:8080/oauth2callback") -> str:
        """Generate Google OAuth 2.0 authorization URL."""
        scopes = f"{GMAIL_READONLY_SCOPE} {GMAIL_SEND_SCOPE}"
        return (
            f"https://accounts.google.com/o/oauth2/v2/auth?"
            f"client_id={client_id}&"
            f"redirect_uri={redirect_uri}&"
            f"response_type=code&"
            f"scope={scopes}&"
            f"access_type=offline&"
            f"prompt=consent"
        )

    def exchange_code(self, code: str, client_id: str, client_secret: str, redirect_uri: str = "http://localhost:8080/oauth2callback") -> Dict[str, Any]:
        """Exchange auth code for access & refresh tokens."""
        token_url = "https://oauth2.googleapis.com/token"
        payload = {
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(token_url, data=payload)
            resp.raise_for_status()
            data = resp.json()
            self._access_token = data.get("access_token")
            self.token_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
            return data

    def disconnect(self) -> bool:
        """Revoke or delete stored credentials."""
        self._access_token = None
        if self.token_file.exists():
            self.token_file.unlink()
        return True

    def fetch_messages(self, query: str = "label:INBOX", max_results: int = 10) -> List[MessageRecord]:
        """Fetch messages matching search query via Gmail API."""
        if not self.is_connected():
            return []

        headers = {"Authorization": f"Bearer {self._access_token}"}
        url = "https://gmail.googleapis.com/gmail/v1/users/me/messages"
        params = {"q": query, "maxResults": max_results}

        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.get(url, headers=headers, params=params)
                if resp.status_code == 401:
                    logger.warning("Gmail access token expired.")
                    return []
                resp.raise_for_status()
                data = resp.json()
                msg_ids = [m["id"] for m in data.get("messages", [])]

                records = []
                for mid in msg_ids:
                    msg_resp = client.get(f"{url}/{mid}", headers=headers, params={"format": "full"})
                    if msg_resp.status_code == 200:
                        records.append(self._parse_gmail_message(msg_resp.json()))
                return records
        except Exception as e:
            logger.error(f"Failed to fetch Gmail messages: {e}")
            return []

    def send_message(self, recipient: str, subject: str, body: str, thread_id: Optional[str] = None) -> Dict[str, Any]:
        """Send an approved message via official Gmail API."""
        if not self.is_connected():
            raise RuntimeError("Gmail connector is not authenticated.")

        message = MIMEMultipart()
        message["to"] = recipient
        message["subject"] = subject
        message.attach(MIMEText(body, "plain"))

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        payload: Dict[str, Any] = {"raw": raw}
        if thread_id:
            payload["threadId"] = thread_id

        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
        }
        url = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"

        with httpx.Client(timeout=20.0) as client:
            resp = client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            return resp.json()

    @staticmethod
    def _parse_gmail_message(data: Dict[str, Any]) -> MessageRecord:
        """Parse raw Gmail API JSON response into standard MessageRecord."""
        headers = {h["name"].lower(): h["value"] for h in data.get("payload", {}).get("headers", [])}
        subject = headers.get("subject", "(No Subject)")
        sender = headers.get("from", "unknown")
        recipient = headers.get("to", "me")
        snippet = data.get("snippet", "")

        # Extract body text from parts
        body_text = snippet
        attachments = []
        payload = data.get("payload", {})

        def walk_parts(part: Dict[str, Any]):
            nonlocal body_text
            mime_type = part.get("mimeType", "")
            filename = part.get("filename", "")
            body = part.get("body", {})

            if filename and body.get("attachmentId"):
                attachments.append(
                    AttachmentMetadata(
                        attachment_id=body["attachmentId"],
                        filename=filename,
                        content_type=mime_type,
                        size_bytes=body.get("size", 0),
                        source_message_id=data.get("id"),
                    )
                )
            elif mime_type == "text/plain" and body.get("data"):
                try:
                    decoded = base64.urlsafe_b64decode(body["data"]).decode("utf-8", errors="replace")
                    body_text = decoded
                except Exception:
                    pass

            for subpart in part.get("parts", []):
                walk_parts(subpart)

        walk_parts(payload)

        return MessageRecord(
            message_id=data.get("id", "msg-unknown"),
            channel=ChannelType.GMAIL,
            thread_id=data.get("threadId"),
            sender=sender,
            recipient=recipient,
            subject=subject,
            body_text=body_text,
            raw_snippet=snippet,
            attachments=attachments,
        )
