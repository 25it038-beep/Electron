"""Controlled, secure process and terminal command runner for Electorn AI."""

from __future__ import annotations

import os
import pathlib
import subprocess
import time
from typing import Any, Optional


class ControlledProcessRunner:
    """Executes validated system commands with timeout and cancellation enforcement."""

    # Disallowed commands that compromise system stability
    BLOCKED_COMMANDS = [
        "format",
        "diskpart",
        "bcdedit",
        "reg delete",
        "del /f /s /q c:\\",
        "rmdir /s /q c:\\",
        "drop database",
        "disable-windowsexecutionpolicy",
    ]

    def __init__(self, default_timeout_sec: int = 30) -> None:
        self.default_timeout_sec = default_timeout_sec
        self.current_process: Optional[subprocess.Popen] = None

    def is_command_safe(self, command: str) -> tuple[bool, str]:
        """Check if command contains destructive or unauthorized instructions."""
        lower = command.strip().lower()
        for blocked in self.BLOCKED_COMMANDS:
            if blocked in lower:
                return False, f"Command contains blocked pattern '{blocked}' (Security Level 3 violation)."
        return True, "Command is safe to execute."

    def run_command(
        self,
        command: str,
        cwd: Optional[str | pathlib.Path] = None,
        timeout_sec: Optional[int] = None,
        env_vars: Optional[dict[str, str]] = None,
    ) -> dict[str, Any]:
        """Execute command in controlled subprocess and capture full output."""
        is_safe, reason = self.is_command_safe(command)
        if not is_safe:
            return {
                "success": False,
                "command": command,
                "exit_code": -1,
                "stdout": "",
                "stderr": reason,
                "duration_ms": 0,
                "timed_out": False,
                "message": reason,
            }

        effective_timeout = timeout_sec or self.default_timeout_sec
        working_dir = str(pathlib.Path(cwd).resolve()) if cwd else os.getcwd()

        start_time = time.time()
        try:
            env = os.environ.copy()
            if env_vars:
                env.update(env_vars)

            proc = subprocess.Popen(
                command,
                cwd=working_dir,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
            )
            self.current_process = proc

            try:
                stdout, stderr = proc.communicate(timeout=effective_timeout)
                duration_ms = int((time.time() - start_time) * 1000)
                exit_code = proc.returncode

                return {
                    "success": exit_code == 0,
                    "command": command,
                    "exit_code": exit_code,
                    "stdout": stdout.strip(),
                    "stderr": stderr.strip(),
                    "duration_ms": duration_ms,
                    "timed_out": False,
                    "message": f"Command finished with exit code {exit_code} in {duration_ms}ms.",
                }
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.communicate()
                duration_ms = int((time.time() - start_time) * 1000)
                return {
                    "success": False,
                    "command": command,
                    "exit_code": -1,
                    "stdout": "",
                    "stderr": f"Command timed out after {effective_timeout} seconds.",
                    "duration_ms": duration_ms,
                    "timed_out": True,
                    "message": f"Process exceeded timeout limit ({effective_timeout}s).",
                }
        except Exception as err:
            duration_ms = int((time.time() - start_time) * 1000)
            return {
                "success": False,
                "command": command,
                "exit_code": -1,
                "stdout": "",
                "stderr": str(err),
                "duration_ms": duration_ms,
                "timed_out": False,
                "message": f"Process runner error: {err}",
            }
        finally:
            self.current_process = None

    def cancel_current_process(self) -> bool:
        """Cancel the active subprocess if running."""
        if self.current_process and self.current_process.poll() is None:
            try:
                self.current_process.kill()
                return True
            except Exception:
                pass
        return False
