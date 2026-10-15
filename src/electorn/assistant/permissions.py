"""Permission, approval, and audit enforcement engine for Personal Assistant."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid

from electorn.assistant.schema import ActionItem, ActionStatus, AssistantConfig, PermissionMode


class SecurityPolicyError(PermissionError):
    """Raised when an action violates safety or permission boundaries."""
    pass


class PermissionEngine:
    """Enforces Observe/Assist/Controlled modes, approval checks, and audit trails."""

    def __init__(self, config: Optional[AssistantConfig] = None) -> None:
        self.config = config or AssistantConfig()
        self._ensure_audit_directory()

    def _ensure_audit_directory(self) -> None:
        audit_file = Path(self.config.audit_log_path)
        audit_file.parent.mkdir(parents=True, exist_ok=True)

    def is_action_allowed(self, action: ActionItem) -> bool:
        """Evaluate if an action is permitted under the active permission mode."""
        if self.config.is_paused:
            raise SecurityPolicyError("Personal Assistant is currently PAUSED. All actions suspended.")

        mode = self.config.permission_mode

        # 1. OBSERVE MODE: Strictly forbids any consequential outbound actions
        if mode == PermissionMode.OBSERVE:
            if action.action_type in ("send_email", "send_whatsapp", "place_call", "delete_file", "run_code"):
                raise SecurityPolicyError(
                    f"Action '{action.action_type}' is prohibited in OBSERVE mode. Switch to 'assist' or 'controlled'."
                )
            return True

        # 2. CONTROLLED AUTOMATION MODE: Allows approved recipients / low-risk actions
        if mode == PermissionMode.CONTROLLED:
            if action.status == ActionStatus.APPROVED:
                return True
            # Whitelist evaluation
            if self.config.whitelisted_recipients:
                if action.recipient.lower() in [r.lower() for r in self.config.whitelisted_recipients]:
                    return True
            # If not explicitly whitelisted, still requires approval
            return False

        # 3. ASSIST MODE: Default safety boundary. Consequential actions ALWAYS require explicit approval
        if mode == PermissionMode.ASSIST:
            return action.status == ActionStatus.APPROVED

        return False

    def check_and_authorize(self, action: ActionItem) -> bool:
        """Validate approval signature and parameters before execution."""
        if not self.is_action_allowed(action):
            raise SecurityPolicyError(
                f"Action '{action.action_id}' ({action.action_type} to {action.recipient}) requires explicit user approval."
            )
        return True

    def log_audit(self, event_type: str, details: Dict[str, Any], status: str = "success") -> None:
        """Append an immutable audit entry to the audit log."""
        entry = {
            "event_id": f"evt-{uuid.uuid4().hex[:12]}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "status": status,
            "permission_mode": self.config.permission_mode.value,
            "details": self._sanitize_for_audit(details),
        }
        try:
            with open(self.config.audit_log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception:
            pass

    def get_recent_audit_logs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieve the most recent audit log entries."""
        audit_file = Path(self.config.audit_log_path)
        if not audit_file.exists():
            return []
        entries = []
        try:
            with open(audit_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        entries.append(json.loads(line))
        except Exception:
            return []
        return entries[-limit:]

    @staticmethod
    def _sanitize_for_audit(data: Dict[str, Any]) -> Dict[str, Any]:
        """Redact tokens, credentials, and private keys from audit logs."""
        sanitized = {}
        sensitive_keys = {"token", "secret", "password", "key", "authorization", "api_key", "cookie"}
        for k, v in data.items():
            if any(s in k.lower() for s in sensitive_keys):
                sanitized[k] = "[REDACTED]"
            elif isinstance(v, dict):
                sanitized[k] = PermissionEngine._sanitize_for_audit(v)
            else:
                sanitized[k] = v
        return sanitized
