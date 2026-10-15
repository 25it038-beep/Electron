"""WhatsApp Business Platform connector with webhook validation and compliance."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import httpx

from electorn.assistant.schema import AttachmentMetadata, ChannelType, MessageRecord

logger = logging.getLogger(__name__)


class WhatsAppConnector:
    """Official Meta WhatsApp Business Cloud API connector."""

    def __init__(
        self,
        phone_number_id: Optional[str] = None,
        access_token: Optional[str] = None,
        verify_token: Optional[str] = None,
        app_secret: Optional[str] = None,
    ) -> None:
        self.phone_number_id = phone_number_id or os.environ.get("WHATSAPP_PHONE_NUMBER_ID")
        self.access_token = access_token or os.environ.get("WHATSAPP_ACCESS_TOKEN")
        self.verify_token = verify_token or os.environ.get("WHATSAPP_VERIFY_TOKEN", "electorn_secure_token")
        self.app_secret = app_secret or os.environ.get("WHATSAPP_APP_SECRET")
        self.api_version = "v21.0"
        self.base_url = f"https://graph.facebook.com/{self.api_version}"

    def is_configured(self) -> bool:
        """Check if required Cloud API credentials are provided."""
        return bool(self.phone_number_id and self.access_token)

    def verify_webhook(self, mode: str, token: str, challenge: str) -> Optional[str]:
        """Validate Meta webhook handshake."""
        if mode == "subscribe" and token == self.verify_token:
            return challenge
        return None

    def validate_signature(self, payload_bytes: bytes, signature_header: str) -> bool:
        """Verify HMAC-SHA256 signature for incoming webhooks."""
        if not self.app_secret:
            # If secret not configured in local testing, bypass with warning
            logger.warning("WhatsApp app_secret not configured; skipping HMAC verification.")
            return True

        if not signature_header or not signature_header.startswith("sha256="):
            return False

        expected_hash = signature_header.split("sha256=")[1]
        calculated_hash = hmac.new(
            self.app_secret.encode("utf-8"),
            payload_bytes,
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(calculated_hash, expected_hash)

    def parse_webhook_payload(self, data: Dict[str, Any]) -> List[MessageRecord]:
        """Extract MessageRecord entries from incoming WhatsApp webhook JSON."""
        messages: List[MessageRecord] = []
        try:
            entry_list = data.get("entry", [])
            for entry in entry_list:
                for change in entry.get("changes", []):
                    value = change.get("value", {})
                    contacts = {c["wa_id"]: c.get("profile", {}).get("name", "") for c in value.get("contacts", [])}
                    for msg in value.get("messages", []):
                        sender_id = msg.get("from", "")
                        sender_name = contacts.get(sender_id, sender_id)
                        msg_type = msg.get("type", "text")
                        msg_id = msg.get("id", f"wa-{msg.get('timestamp')}")
                        body_text = ""
                        attachments = []

                        if msg_type == "text":
                            body_text = msg.get("text", {}).get("body", "")
                        elif msg_type in ("document", "image", "audio", "video"):
                            media = msg.get(msg_type, {})
                            body_text = media.get("caption", f"[{msg_type.upper()} Attachment]")
                            attachments.append(
                                AttachmentMetadata(
                                    attachment_id=media.get("id", ""),
                                    filename=media.get("filename", f"whatsapp_{msg_type}_{msg_id}"),
                                    content_type=media.get("mime_type", "application/octet-stream"),
                                    sha256_hash=media.get("sha256"),
                                    source_message_id=msg_id,
                                )
                            )

                        messages.append(
                            MessageRecord(
                                message_id=msg_id,
                                channel=ChannelType.WHATSAPP,
                                sender=f"{sender_name} ({sender_id})",
                                recipient=self.phone_number_id or "me",
                                body_text=body_text,
                                attachments=attachments,
                                metadata={"raw_type": msg_type},
                            )
                        )
        except Exception as e:
            logger.error(f"Error parsing WhatsApp webhook payload: {e}")
        return messages

    def send_text_message(self, recipient_phone: str, text: str) -> Dict[str, Any]:
        """Send an approved WhatsApp message via Cloud API."""
        if not self.is_configured():
            raise RuntimeError("WhatsApp Cloud API connector is not configured.")

        url = f"{self.base_url}/{self.phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        # Format clean digits
        clean_recipient = "".join(filter(str.isdigit, recipient_phone))
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": clean_recipient,
            "type": "text",
            "text": {"preview_url": False, "body": text},
        }

        with httpx.Client(timeout=20.0) as client:
            resp = client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            return resp.json()
