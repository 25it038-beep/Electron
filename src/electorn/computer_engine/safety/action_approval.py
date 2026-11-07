"""Interactive confirmation manager for high-risk actions."""

from __future__ import annotations

import time
import uuid
from typing import Callable, Dict, List, Optional

from ..types import ActionPayload


class ActionApproval:
    """Handles user approval requests before executing consequential operations."""

    def __init__(self) -> None:
        self._pending: Dict[str, dict] = {}
        self._handler: Optional[Callable[[dict], bool]] = None

    def set_approval_handler(self, handler: Callable[[dict], bool]) -> None:
        self._handler = handler

    def request_approval(self, action: ActionPayload, reason: str, timeout_seconds: float = 30.0) -> bool:
        req_id = f"req_{uuid.uuid4().hex[:6]}"
        req = {
            "request_id": req_id,
            "action": action,
            "reason": reason,
            "timestamp": time.time(),
            "timeout": timeout_seconds,
            "status": "pending",
        }
        self._pending[req_id] = req

        if self._handler:
            try:
                approved = self._handler(req)
                req["status"] = "approved" if approved else "denied"
                self._pending.pop(req_id, None)
                return approved
            except Exception:
                req["status"] = "denied"
                self._pending.pop(req_id, None)
                return False

        # If no interactive handler registered, default to safe require confirmation
        return False

    def resolve_request(self, req_id: str, approved: bool) -> bool:
        if req_id in self._pending:
            self._pending[req_id]["status"] = "approved" if approved else "denied"
            return True
        return False

    def get_status(self, action_id: str) -> str:
        for req in self._pending.values():
            action = req.get("action")
            if getattr(action, "action_id", None) == action_id:
                return req.get("status", "unknown")
        return "approved"
