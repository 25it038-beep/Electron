"""Cross-platform command runner with timeout and permission guardrails."""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path
from typing import Optional
from pydantic import BaseModel
from electorn.workspace.permissions import PermissionManager


class ExecutionResult(BaseModel):
    """Result of a shell command execution."""

    command: str
    returncode: int
    stdout: str
    stderr: str
    duration_ms: float
    timed_out: bool = False
    permitted: bool = True

    @property
    def is_success(self) -> bool:
        return self.returncode == 0 and not self.timed_out and self.permitted


class CommandRunner:
    """Executes platform-aware CLI commands within the project workspace."""

    def __init__(
        self,
        workspace_dir: Path | str,
        permissions: Optional[PermissionManager] = None,
        default_timeout: int = 120,
    ):
        self.workspace_dir = Path(workspace_dir).resolve()
        self.permissions = permissions or PermissionManager(auto_approve=True)
        self.default_timeout = default_timeout

    def run(
        self,
        command: str,
        timeout: Optional[int] = None,
        env_vars: Optional[dict[str, str]] = None,
        require_permission: bool = True,
    ) -> ExecutionResult:
        """Run a shell command inside workspace with timeout and output capture."""
        if require_permission:
            allowed = self.permissions.request_command_execution(command)
            if not allowed:
                return ExecutionResult(
                    command=command,
                    returncode=-1,
                    stdout="",
                    stderr="Execution rejected by permission policy.",
                    duration_ms=0,
                    permitted=False,
                )

        t_limit = timeout or self.default_timeout
        start_time = time.time()

        env = os.environ.copy()
        if env_vars:
            env.update(env_vars)

        # Force UTF-8 encoding for Python subprocesses
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUNBUFFERED"] = "1"

        try:
            process = subprocess.run(
                command,
                cwd=str(self.workspace_dir),
                shell=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=t_limit,
                env=env,
            )
            duration_ms = (time.time() - start_time) * 1000
            return ExecutionResult(
                command=command,
                returncode=process.returncode,
                stdout=process.stdout or "",
                stderr=process.stderr or "",
                duration_ms=duration_ms,
                timed_out=False,
                permitted=True,
            )
        except subprocess.TimeoutExpired as exc:
            duration_ms = (time.time() - start_time) * 1000
            return ExecutionResult(
                command=command,
                returncode=-1,
                stdout=exc.stdout if isinstance(exc.stdout, str) else "",
                stderr=f"Command timed out after {t_limit} seconds.",
                duration_ms=duration_ms,
                timed_out=True,
                permitted=True,
            )
        except Exception as exc:
            duration_ms = (time.time() - start_time) * 1000
            return ExecutionResult(
                command=command,
                returncode=-1,
                stdout="",
                stderr=f"Execution failed with exception: {exc}",
                duration_ms=duration_ms,
                timed_out=False,
                permitted=True,
            )
