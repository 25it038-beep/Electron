"""Permission evaluation and destructive command interception."""

from __future__ import annotations

import re
from typing import List

from ..types import ActionPayload, RiskLevel


class PermissionManager:
    """Classifies risk levels and prevents unauthorized destructive operations."""

    BLOCKED_PATTERNS: List[re.Pattern] = [
        re.compile(r"format\s+[a-z]:", re.IGNORECASE),
        re.compile(r"rmdir\s+/s\s+/q\s+c:\\", re.IGNORECASE),
        re.compile(r"reg\s+delete", re.IGNORECASE),
        re.compile(r"drop\s+database", re.IGNORECASE),
        re.compile(r"rm\s+-rf\s+/(?:\s|$)", re.IGNORECASE),
    ]

    HIGH_RISK_KEYWORDS = [
        "delete_file", "purchase", "send_email", "submit_payment", "wipe", "truncate"
    ]

    def __init__(self, auto_approve_low_risk: bool = True) -> None:
        self.auto_approve_low_risk = auto_approve_low_risk

    def evaluate_risk(self, action: ActionPayload) -> RiskLevel:
        """Categorize action into SAFE, LOW_RISK, HIGH_RISK_CONFIRM, or BLOCKED."""
        # Check blocked patterns
        if action.text:
            for pat in self.BLOCKED_PATTERNS:
                if pat.search(action.text):
                    return RiskLevel.BLOCKED

        # Check high-risk actions
        if action.type in self.HIGH_RISK_KEYWORDS or action.requires_confirmation:
            return RiskLevel.HIGH_RISK_CONFIRM

        if action.text and any(w in action.text.lower() for w in ["del /f", "rm -rf", "drop table", "shutdown"]):
            return RiskLevel.HIGH_RISK_CONFIRM

        # Standard interactive actions
        if action.category in ("mouse", "keyboard", "window", "browser", "system"):
            return RiskLevel.SAFE if self.auto_approve_low_risk else RiskLevel.LOW_RISK

        return RiskLevel.LOW_RISK

    def requires_confirmation(self, action: ActionPayload) -> bool:
        """Determine if action requires explicit user approval."""
        risk = self.evaluate_risk(action)
        return risk == RiskLevel.HIGH_RISK_CONFIRM or action.requires_confirmation

    def is_permitted(self, action: ActionPayload) -> bool:
        return self.evaluate_risk(action) != RiskLevel.BLOCKED
