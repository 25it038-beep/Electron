"""Permission guardrails for file operations and system execution."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable, Optional


class PermissionManager:
    """Controls whether autonomous operations proceed or prompt user."""

    def __init__(self, auto_approve: bool = False, prompt_fn: Optional[Callable[[str], bool]] = None):
        self.auto_approve = auto_approve
        self.prompt_fn = prompt_fn or self._default_cli_prompt

    def _default_cli_prompt(self, question: str) -> bool:
        """Prompt user via terminal stdin."""
        # In non-interactive environments (CI or pipes), default to False if not auto-approved
        if not sys.stdin.isatty():
            return False
        reply = input(f"{question} [y/N]: ").strip().lower()
        return reply in ("y", "yes")

    def request_file_write(self, file_path: Path, is_overwrite: bool = False) -> bool:
        """Request permission to create or overwrite a file."""
        if self.auto_approve or not is_overwrite:
            return True
        return self.prompt_fn(f"⚠️  Allow modifying existing file '{file_path}'?")

    def request_command_execution(self, command: str) -> bool:
        """Request permission to execute a shell command (e.g. pip install, npm test)."""
        if self.auto_approve:
            return True
        return self.prompt_fn(f"⚠️  Allow running command: '{command}'?")
