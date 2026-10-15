"""Multi-Agent Coordinator orchestrating Communication, Reply, File Intelligence, Calling, Task, and Supervisor agents."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid

from electorn.assistant.calling import MockTelephonyProvider, TwilioTelephonyProvider
from electorn.assistant.email_connector import GmailConnector
from electorn.assistant.file_intelligence import FileIntelligenceEngine
from electorn.assistant.permissions import PermissionEngine, SecurityPolicyError
from electorn.assistant.schema import (
    ActionItem,
    ActionStatus,
    AssistantConfig,
    CallBriefing,
    CallRecord,
    ChannelType,
    DocumentAnalysisReport,
    ExtractedTask,
    MessageRecord,
    PermissionMode,
    WritingStyle,
)
from electorn.assistant.storage import AssistantStorage
from electorn.assistant.tasks import TaskEngine
from electorn.assistant.whatsapp_connector import WhatsAppConnector
from electorn.runtime.ollama_client import OllamaClient
from electorn.storage.config import Config

logger = logging.getLogger(__name__)


class AssistantSupervisor:
    """Central orchestrator managing multi-agent workflows, permission enforcement, and state."""

    def __init__(self, config: Optional[Config] = None, client: Optional[OllamaClient] = None) -> None:
        self.app_config = config
        self.client = client or OllamaClient(auto_initialize=False, mock_mode=False)
        self.storage = AssistantStorage()
        self.assistant_cfg = self.storage.load_config()
        self.permissions = PermissionEngine(self.assistant_cfg)

        # Subsystems
        self.email_connector = GmailConnector()
        self.whatsapp_connector = WhatsAppConnector()
        self.file_engine = FileIntelligenceEngine(
            download_dir=Path(self.assistant_cfg.downloads_directory),
            max_size_mb=self.assistant_cfg.max_attachment_size_mb,
        )
        self.task_engine = TaskEngine()
        self.telephony = (
            TwilioTelephonyProvider()
            if self.assistant_cfg.telephony_provider == "twilio"
            else MockTelephonyProvider()
        )

    # =========================================================================
    # 1. STATUS & LIFECYCLE
    # =========================================================================

    def get_status(self) -> Dict[str, Any]:
        """Return comprehensive health and configuration status."""
        recent_msgs = self.storage.list_messages(limit=5)
        pending_actions = self.storage.list_actions(status=ActionStatus.PENDING_APPROVAL)
        pending_tasks = self.storage.list_tasks()

        return {
            "permission_mode": self.assistant_cfg.permission_mode.value,
            "is_paused": self.assistant_cfg.is_paused,
            "default_writing_style": self.assistant_cfg.default_writing_style.value,
            "integrations": {
                "gmail": "connected" if self.email_connector.is_connected() else "disconnected",
                "whatsapp": "configured" if self.whatsapp_connector.is_configured() else "not_configured",
                "telephony": self.assistant_cfg.telephony_provider,
            },
            "stats": {
                "total_stored_messages": len(self.storage.list_messages(limit=500)),
                "pending_approvals": len(pending_actions),
                "active_tasks": len([t for t in pending_tasks if t.status.value == "pending"]),
            },
            "recent_messages": [f"[{m.channel.value.upper()}] From: {m.sender} | {m.subject or m.body_text[:40]}" for m in recent_msgs],
        }

    def pause(self) -> str:
        """Globally suspend all autonomous activities and actions."""
        self.assistant_cfg.is_paused = True
        self.storage.save_config(self.assistant_cfg)
        self.permissions.log_audit("assistant_paused", {"status": "paused"})
        return "Personal Assistant has been paused. All external communication is frozen."

    def resume(self) -> str:
        """Resume assistant operations."""
        self.assistant_cfg.is_paused = False
        self.storage.save_config(self.assistant_cfg)
        self.permissions.log_audit("assistant_resumed", {"status": "active"})
        return "Personal Assistant resumed active monitoring and assistance."

    def set_mode(self, mode_str: str) -> str:
        """Switch operational mode between observe, assist, and controlled."""
        try:
            mode = PermissionMode(mode_str.lower())
            self.assistant_cfg.permission_mode = mode
            self.storage.save_config(self.assistant_cfg)
            self.permissions.config = self.assistant_cfg
            self.permissions.log_audit("mode_changed", {"new_mode": mode.value})
            return f"Operational mode updated to: {mode.value.upper()}"
        except Exception:
            raise ValueError(f"Invalid mode '{mode_str}'. Must be one of: observe, assist, controlled.")

    # =========================================================================
    # 2. COMMUNICATION AGENT (Ingestion & Summaries)
    # =========================================================================

    def sync_email(self, query: str = "label:INBOX", max_count: int = 10) -> List[MessageRecord]:
        """Fetch and store recent Gmail messages, extracting tasks automatically."""
        if self.assistant_cfg.is_paused:
            return []

        records = self.email_connector.fetch_messages(query=query, max_results=max_count)
        new_count = 0
        for r in records:
            self.storage.save_message(r)
            new_count += 1
            # Extract tasks
            tasks = self.task_engine.extract_tasks_from_text(
                f"{r.subject}\n{r.body_text}",
                source_type="gmail",
                source_id=r.message_id
            )
            for t in tasks:
                self.storage.save_task(t)

        self.permissions.log_audit("sync_email", {"fetched": len(records), "new_saved": new_count})
        return records

    def sync_whatsapp(self, payload: Dict[str, Any]) -> List[MessageRecord]:
        """Process incoming WhatsApp webhook payload securely."""
        if self.assistant_cfg.is_paused:
            return []

        records = self.whatsapp_connector.parse_webhook_payload(payload)
        for r in records:
            self.storage.save_message(r)
            tasks = self.task_engine.extract_tasks_from_text(
                r.body_text,
                source_type="whatsapp",
                source_id=r.message_id
            )
            for t in tasks:
                self.storage.save_task(t)

        self.permissions.log_audit("sync_whatsapp", {"count": len(records)})
        return records

    # =========================================================================
    # 3. REPLY AGENT (Drafting & Verified Sending)
    # =========================================================================

    def draft_reply(self, message_id: str, style_override: Optional[str] = None) -> ActionItem:
        """Draft natural, context-aware reply for human review."""
        msg = self.storage.get_message(message_id)
        if not msg:
            raise ValueError(f"Message ID '{message_id}' not found in local communication history.")

        style = style_override or self.assistant_cfg.default_writing_style.value

        # Synthesize draft using local AI client or reliable heuristic
        prompt = (
            f"You are the Electorn Personal Reply Agent.\n"
            f"Draft a concise, natural reply in a {style} tone.\n"
            f"Do not invent facts, promises, or attachments.\n\n"
            f"Incoming Message:\n"
            f"From: {msg.sender}\n"
            f"Subject: {msg.subject}\n"
            f"Body:\n{msg.body_text}\n\n"
            f"Reply Draft:"
        )

        draft_content = ""
        try:
            if self.client.is_available():
                resp = self.client.generate(
                    model="llama3.2:1b",
                    prompt=prompt,
                    temperature=0.3,
                )
                draft_content = resp.content.strip()
        except Exception:
            pass

        if not draft_content:
            # Deterministic, professional fallback
            draft_content = (
                f"Hi {msg.sender.split()[0] if msg.sender else 'there'},\n\n"
                f"Thank you for your message regarding '{msg.subject or 'your inquiry'}'. "
                f"I have received your note and will review the details to get back to you shortly.\n\n"
                f"Best regards,\nHarshan"
            )

        action = ActionItem(
            action_type="send_email" if msg.channel == ChannelType.GMAIL else "send_whatsapp",
            channel=msg.channel,
            recipient=msg.sender,
            subject=f"Re: {msg.subject}" if msg.subject and not msg.subject.startswith("Re:") else (msg.subject or "Reply"),
            content=draft_content,
            source_message_id=msg.message_id,
            status=ActionStatus.PENDING_APPROVAL,
        )
        self.storage.save_action(action)
        self.permissions.log_audit("draft_reply", {"message_id": message_id, "action_id": action.action_id})
        return action

    def approve_action(self, action_id: str) -> Dict[str, Any]:
        """Approve and execute a pending consequential action."""
        action = self.storage.get_action(action_id)
        if not action:
            raise ValueError(f"Action '{action_id}' not found.")

        if action.status != ActionStatus.PENDING_APPROVAL:
            raise ValueError(f"Action '{action_id}' is already {action.status.value}.")

        action.status = ActionStatus.APPROVED
        action.approved_at = datetime.now(timezone.utc)

        # Check permission engine
        self.permissions.check_and_authorize(action)

        # Dispatch execution
        try:
            if action.channel == ChannelType.GMAIL:
                res = self.email_connector.send_message(
                    recipient=action.recipient,
                    subject=action.subject or "Notification",
                    body=action.content,
                )
                action.status = ActionStatus.EXECUTED
                action.executed_at = datetime.now(timezone.utc)
                action.execution_result = f"Sent via Gmail API. ID: {res.get('id', 'sent')}"
            elif action.channel == ChannelType.WHATSAPP:
                res = self.whatsapp_connector.send_text_message(
                    recipient_phone=action.recipient,
                    text=action.content,
                )
                action.status = ActionStatus.EXECUTED
                action.executed_at = datetime.now(timezone.utc)
                action.execution_result = f"Sent via WhatsApp Cloud API. ID: {res.get('messages', [{}])[0].get('id', 'sent')}"
            else:
                action.status = ActionStatus.EXECUTED
                action.execution_result = "Action executed."

            self.storage.save_action(action)
            self.permissions.log_audit("action_approved_and_executed", {"action_id": action_id, "result": action.execution_result})
            return {"success": True, "action": action.model_dump(mode="json")}

        except Exception as err:
            action.status = ActionStatus.FAILED
            action.execution_result = str(err)
            self.storage.save_action(action)
            self.permissions.log_audit("action_execution_failed", {"action_id": action_id, "error": str(err)}, status="failed")
            raise

    def reject_action(self, action_id: str, reason: str = "User rejected") -> ActionItem:
        """Reject and cancel a pending action."""
        action = self.storage.get_action(action_id)
        if not action:
            raise ValueError(f"Action '{action_id}' not found.")
        action.status = ActionStatus.REJECTED
        action.execution_result = reason
        self.storage.save_action(action)
        self.permissions.log_audit("action_rejected", {"action_id": action_id, "reason": reason})
        return action

    # =========================================================================
    # 4. FILE INTELLIGENCE AGENT
    # =========================================================================

    def analyze_document(self, file_path_str: str) -> DocumentAnalysisReport:
        """Run deep document intelligence and extract actionable tasks."""
        p = Path(file_path_str)
        report = self.file_engine.analyze_file(p)
        self.storage.save_report(report)

        # Convert findings/deadlines into tracked tasks
        for item in report.deadlines_and_actions:
            clean = item.replace("Action item:", "").replace("Mentioned date/deadline:", "").strip()
            task = ExtractedTask(
                task_id=f"tsk-{uuid.uuid4().hex[:8]}",
                title=clean[:80],
                description=f"Extracted from {p.name}: {item}",
                source_type="file",
                source_id=str(p.name),
            )
            self.storage.save_task(task)

        self.permissions.log_audit("analyze_document", {"file": p.name, "size": report.file_size_bytes})
        return report

    def compare_documents(self, file_a_str: str, file_b_str: str) -> Dict[str, Any]:
        """Compare two documents side-by-side."""
        return self.file_engine.compare_files(Path(file_a_str), Path(file_b_str))

    # =========================================================================
    # 5. CALLING AGENT
    # =========================================================================

    def prepare_call(self, contact: str, phone: str, purpose: str) -> CallBriefing:
        """Prepare call briefing dossier with required AI disclosures."""
        briefing = self.telephony.prepare_briefing(contact, phone, purpose)
        self.permissions.log_audit("prepare_call", {"contact": contact, "purpose": purpose})
        return briefing

    def start_call(self, briefing: CallBriefing) -> CallRecord:
        """Initiate call through telephony gateway with explicit permission check."""
        action = ActionItem(
            action_type="place_call",
            channel=ChannelType.CALL,
            recipient=f"{briefing.contact_name} ({briefing.phone_number})",
            content=briefing.purpose,
            status=ActionStatus.APPROVED,
        )
        self.permissions.check_and_authorize(action)

        record = self.telephony.initiate_call(briefing)
        self.storage.save_call(record)

        # Register follow-up tasks
        for t_title in record.follow_up_tasks:
            self.storage.save_task(
                ExtractedTask(
                    task_id=f"tsk-{uuid.uuid4().hex[:8]}",
                    title=t_title,
                    source_type="call",
                    source_id=record.call_id,
                )
            )

        self.permissions.log_audit("start_call", {"call_id": record.call_id, "contact": record.contact_name})
        return record
