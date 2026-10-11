"""Cross-platform secure command runner with timeout and permission guardrails."""

from __future__ import annotations

import os
import shlex
import subprocess
import time
from pathlib import Path
from typing import Optional, Union
from pydantic import BaseModel, Field
from electorn.workspace.permissions import PermissionManager


class ExecutionResult(BaseModel):
    """Result of a command execution."""

    command: str
    returncode: int
    stdout: str
    stderr: str
    duration_ms: float
    timed_out: bool = False
    permitted: bool = True
    dry_run: bool = False

    @property
    def is_success(self) -> bool:
        return self.returncode == 0 and not self.timed_out and self.permitted


class CommandRunner:
    """Executes platform-aware CLI commands within the project workspace securely."""

    def __init__(
        self,
        workspace_dir: Path | str,
        permissions: Optional[PermissionManager] = None,
        default_timeout: int = 120,
        dry_run: bool = False,
    ):
        self.workspace_dir = Path(workspace_dir).resolve()
        self.permissions = permissions or PermissionManager(auto_approve=True)
        self.default_timeout = default_timeout
        self.dry_run = dry_run
        self.command_history: list[ExecutionResult] = []

    def run(
        self,
        command: Union[str, list[str]],
        timeout: Optional[int] = None,
        env_vars: Optional[dict[str, str]] = None,
        require_permission: bool = True,
        dry_run: Optional[bool] = None,
    ) -> ExecutionResult:
        """Run command with timeout, output capture, and argument array security."""
        cmd_str = command if isinstance(command, str) else " ".join(command)
        is_dry = self.dry_run if dry_run is None else dry_run

        if is_dry:
            result = ExecutionResult(
                command=cmd_str,
                returncode=0,
                stdout="[Dry-run mode: command simulated successfully]",
                stderr="",
                duration_ms=0,
                permitted=True,
                dry_run=True,
            )
            self.command_history.append(result)
            return result

        if require_permission:
            allowed = self.permissions.request_command_execution(cmd_str)
            if not allowed:
                result = ExecutionResult(
                    command=cmd_str,
                    returncode=-1,
                    stdout="",
                    stderr="Execution rejected by permission policy.",
                    duration_ms=0,
                    permitted=False,
                )
                self.command_history.append(result)
                return result

        t_limit = timeout or self.default_timeout
        start_time = time.time()

        env = os.environ.copy()
        if env_vars:
            env.update(env_vars)

        # Force UTF-8 encoding for Python subprocesses
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUNBUFFERED"] = "1"

        try:
            # On Windows or with string commands, run with shell=True; if list, can run safely
            use_shell = isinstance(command, str)
            process = subprocess.run(
                command,
                cwd=str(self.workspace_dir),
                shell=use_shell,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=t_limit,
                env=env,
            )
            duration_ms = (time.time() - start_time) * 1000
            result = ExecutionResult(
                command=cmd_str,
                returncode=process.returncode,
                stdout=process.stdout or "",
                stderr=process.stderr or "",
                duration_ms=duration_ms,
                timed_out=False,
                permitted=True,
            )
            self.command_history.append(result)
            return result
        except subprocess.TimeoutExpired as exc:
            duration_ms = (time.time() - start_time) * 1000
            result = ExecutionResult(
                command=cmd_str,
                returncode=-1,
                stdout=exc.stdout if isinstance(exc.stdout, str) else "",
                stderr=f"Command timed out after {t_limit} seconds.",
                duration_ms=duration_ms,
                timed_out=True,
                permitted=True,
            )
            self.command_history.append(result)
            return result
        except Exception as exc:
            duration_ms = (time.time() - start_time) * 1000
            result = ExecutionResult(
                command=cmd_str,
                returncode=-1,
                stdout="",
                stderr=f"Execution failed with exception: {exc}",
                duration_ms=duration_ms,
                timed_out=False,
                permitted=True,
            )
            self.command_history.append(result)
            return result
