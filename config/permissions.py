"""Security, Permissions, and Safety Policy for Electorn AI.

Enforces a 3-tier permission model:
- Level 1 (Safe): Autonomous execution without user interruption.
- Level 2 (Confirm): Requires explicit user approval before execution.
- Level 3 (Restricted): Strictly prohibited, permanently blocked.
"""

from __future__ import annotations

import enum
import os
import pathlib
import re
from typing import Any, Optional


class PermissionLevel(enum.IntEnum):
    """Action risk classification levels."""
    LEVEL_1_SAFE = 1        # Non-destructive, reading, browsing, launching approved apps
    LEVEL_2_CONFIRM = 2     # Modifying files, overwriting, form submission, commands
    LEVEL_3_RESTRICTED = 3  # System destruction, credential theft, security bypass


class PermissionManager:
    """Evaluates proposed actions against security rules and approved policies."""

    # Allowed safe tools list
    LEVEL_1_TOOLS = {
        "browser.open_url",
        "browser.search",
        "browser.scroll",
        "browser.navigate",
        "browser.screenshot",
        "browser.extract_table",
        "browser.read_text",
        "os.launch_app",
        "os.focus_window",
        "os.minimize_windows",
        "os.maximize_window",
        "os.switch_window",
        "os.volume",
        "os.media",
        "os.system_specs",
        "os.list_processes",
        "os.open_folder",
        "file.read_file",
        "file.create_file",       # When file does not already exist
        "file.create_folder",
    }

    # Tools that require user confirmation
    LEVEL_2_TOOLS = {
        "file.overwrite_file",
        "file.delete_file",
        "file.delete_folder",
        "file.move_files",
        "browser.submit_form",
        "browser.click_payment",
        "process.run_command",
        "os.close_app",
        "os.lock_workstation",
        "file.empty_recycle_bin",
    }

    # Strictly forbidden patterns in commands or scripts
    DANGEROUS_PATTERNS = [
        r"\bformat\b",
        r"\brmdir\s+/[sS]",
        r"\bdel\s+/[fF]\s+/[sS]",
        r"\bdrop\s+database\b",
        r"\bnet\s+user\b",
        r"\bSet-ExecutionPolicy\b",
        r"\bDisable-WindowsOptionalFeature\b",
        r"\bStop-Service\s+(?:windefend|mpssvc)\b",
        r"\breg\s+delete\b",
        r"\bInvoke-Expression\b.*(?:http|token|pass)",
    ]

    def __init__(self, allowed_directories: Optional[list[str]] = None) -> None:
        self.allowed_directories = allowed_directories or [
            str(pathlib.Path.home() / "Desktop"),
            str(pathlib.Path.home() / "Documents"),
            str(pathlib.Path.home() / "Downloads"),
            str(pathlib.Path.cwd()),
        ]

    def check_action(self, action_name: str, parameters: dict[str, Any]) -> PermissionLevel:
        """Alias for classify_action."""
        return self.classify_action(action_name, parameters)

    def classify_action(self, action_name: str, parameters: dict[str, Any]) -> PermissionLevel:
        """Classify action risk level based on tool and parameters."""
        # 1. Check for Level 3 Restricted keywords / commands
        if action_name == "process.run_command":
            cmd = str(parameters.get("command", "")).lower()
            for pattern in self.DANGEROUS_PATTERNS:
                if re.search(pattern, cmd, re.IGNORECASE):
                    return PermissionLevel.LEVEL_3_RESTRICTED

        # Credential or token theft checks
        if any(bad in str(parameters).lower() for bad in ["extract_password", "steal_cookies", "bypass_mfa", "bypass_captcha"]):
            return PermissionLevel.LEVEL_3_RESTRICTED

        # 2. Check Level 2 Confirm actions
        if action_name in self.LEVEL_2_TOOLS:
            return PermissionLevel.LEVEL_2_CONFIRM

        # File creation when target already exists is an overwrite (Level 2)
        if action_name == "file.create_file":
            target_path = parameters.get("path")
            if target_path and pathlib.Path(target_path).exists():
                return PermissionLevel.LEVEL_2_CONFIRM

        # Default to Level 1 if tool is in safe list
        if action_name in self.LEVEL_1_TOOLS:
            return PermissionLevel.LEVEL_1_SAFE

        # Any unknown action requires confirmation
        return PermissionLevel.LEVEL_2_CONFIRM

    def validate_action(
        self,
        action_name: str,
        parameters: dict[str, Any],
        user_confirmed: bool = False,
    ) -> tuple[bool, str]:
        """Validate whether the proposed action is permitted to run.

        Returns (is_allowed, reason).
        """
        level = self.classify_action(action_name, parameters)

        if level == PermissionLevel.LEVEL_3_RESTRICTED:
            return False, f"Action '{action_name}' is RESTRICTED (Level 3 violation: potential security risk)."

        if level == PermissionLevel.LEVEL_2_CONFIRM:
            if not user_confirmed:
                return False, f"Action '{action_name}' requires explicit user confirmation (Level 2)."
            return True, "User confirmed Level 2 action."

        # Level 1 Safe action
        return True, "Safe action permitted (Level 1)."

    def is_path_allowed(self, target_path: str | pathlib.Path) -> bool:
        """Ensure path operations do not target root OS directories."""
        try:
            resolved = pathlib.Path(target_path).resolve()
            # Block Windows system root modification
            win_dir = os.environ.get("WINDIR", "C:\\Windows")
            if str(resolved).lower().startswith(win_dir.lower()):
                return False
            return True
        except Exception:
            return False
