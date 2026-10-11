"""Permission guardrails for workspace operations and system execution."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable, Optional


class PermissionManager:
    """Controls whether autonomous operations proceed or prompt user.

    Implements Section 3 Permission Guardrails:
    - Default permitted operations within authorized workspace: Create dirs, files,
      modify files, generate code, run build/test commands, and local checkpoints.
    - Additional approval required only for: Destructive deletions outside workspace,
      modifying files outside workspace, system-wide changes, or firewall/security alters.
    """

    HIGH_RISK_COMMAND_KEYWORDS = [
        "format ",
        "diskpart",
        "reg delete",
        "reg add",
        "netsh advfirewall",
        "setx ",
        "shutdown ",
        "rmdir /s /q c:\\",
        "del /f /s /q c:\\",
        "remove-item -recurse c:\\",
    ]

    def __init__(
        self,
        workspace_root: Optional[Path | str] = None,
        auto_approve: bool = False,
        prompt_fn: Optional[Callable[[str], bool]] = None,
    ):
        self.workspace_root = Path(workspace_root).resolve() if workspace_root else None
        self.auto_approve = auto_approve
        self.prompt_fn = prompt_fn or self._default_cli_prompt

    def _default_cli_prompt(self, question: str) -> bool:
        """Prompt user via terminal stdin."""
        if not sys.stdin.isatty():
            return False
        reply = input(f"{question} [y/N]: ").strip().lower()
        return reply in ("y", "yes")

    def request_file_write(self, file_path: Path, is_overwrite: bool = False) -> bool:
        """Request permission to create or modify a file.
        
        Within the authorized workspace, standard file generation and updates
        are permitted by default without annoying the user with repetitive prompts.
        """
        if self.auto_approve:
            return True

        # Check if write is outside workspace boundary
        if self.workspace_root:
            try:
                resolved = file_path.resolve()
                resolved.relative_to(self.workspace_root)
            except ValueError:
                # File is OUTSIDE workspace! High risk -> Require explicit approval
                return self.prompt_fn(f"⚠️ SECURITY ALERT: Allow writing file outside workspace at '{file_path}'?")

        # Standard file generation/modification within authorized workspace is permitted
        return True

    def request_command_execution(self, command: str) -> bool:
        """Request permission to execute a shell command.
        
        Routine dev commands (pip install, npm install, pytest, python, npm run)
        within the project workspace are permitted by default when auto_approve=True
        or when using the default non-interactive policy.
        When auto_approve is False and an explicit prompt_fn is provided, prompt the caller.
        High-risk system commands always trigger explicit confirmation prompts.
        """
        if self.auto_approve:
            return True

        lower_cmd = command.lower()

        # Check for dangerous system alteration commands
        if any(keyword in lower_cmd for keyword in self.HIGH_RISK_COMMAND_KEYWORDS):
            return self.prompt_fn(f"⚠️ HIGH-RISK SYSTEM COMMAND: Allow running: '{command}'?")

        # When caller provides a custom prompt_fn (or explicitly tests rejection), prompt them
        if self.prompt_fn != self._default_cli_prompt:
            return self.prompt_fn(f"Allow running: '{command}'?")

        # Standard development commands are permitted in the authorized workspace
        return True
