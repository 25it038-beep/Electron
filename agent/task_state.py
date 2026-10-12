"""Task lifecycle state enumeration and transitions for Electorn AI."""

from __future__ import annotations

import enum


class TaskLifecycleState(enum.Enum):
    """Enforces the strict autonomous AI agent execution lifecycle."""
    IDLE = "IDLE"
    UNDERSTAND = "UNDERSTAND"
    PLAN = "PLAN"
    VALIDATE = "VALIDATE"
    REQUEST_APPROVAL = "REQUEST_APPROVAL"
    EXECUTE = "EXECUTE"
    OBSERVE = "OBSERVE"
    VERIFY = "VERIFY"
    RECOVER = "RECOVER"
    REPORT = "REPORT"
    PAUSED = "PAUSED"
    FAILED = "FAILED"
