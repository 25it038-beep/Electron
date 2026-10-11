"""Dedicated PowerShell Execution Engine for Windows development automation."""

from __future__ import annotations

import json
import os
import re
import shutil
import signal
import subprocess
import time
from pathlib import Path
from typing import Optional, Union
from pydantic import BaseModel, Field

from electorn.workspace.permissions import PermissionManager


class PowerShellCommandResult(BaseModel):
    """Result of a command executed via PowerShell."""

    command: str
    returncode: int
    stdout: str
    stderr: str
    duration_ms: float
    timed_out: bool = False
    permitted: bool = True
    powershell_exe: str = "powershell.exe"

    @property
    def is_success(self) -> bool:
        return self.returncode == 0 and not self.timed_out and self.permitted


class ProcessInfo(BaseModel):
    """Metadata describing a background process started by Electorn."""

    pid: int
    name: str
    command: str
    workspace_dir: str
    start_time: float
    port: Optional[int] = None
    is_running: bool = True


class PowerShellExecutionEngine:
    """Controls execution of scripts, commands, and background dev servers via PowerShell."""

    def __init__(
        self,
        workspace_dir: Path | str,
        permissions: Optional[PermissionManager] = None,
        default_timeout: int = 180,
    ):
        self.workspace_dir = Path(workspace_dir).resolve()
        self.permissions = permissions or PermissionManager(workspace_root=self.workspace_dir, auto_approve=True)
        self.default_timeout = default_timeout
        self.ps_exe = self._detect_powershell()
        self.ps_version = self._detect_version()
        self.process_file = self.workspace_dir / ".electorn" / "processes.json"

    @property
    def executable(self) -> str:
        """Path or command name of the PowerShell executable."""
        return self.ps_exe

    @property
    def powershell_version(self) -> str:
        """Detected PowerShell version."""
        return self.ps_version

    def _detect_powershell(self) -> str:
        """Find the best available PowerShell executable on the host."""
        # Prefer modern PowerShell Core (pwsh.exe) if installed, fallback to Windows PowerShell
        pwsh = shutil.which("pwsh.exe") or shutil.which("pwsh")
        if pwsh:
            return pwsh
        powershell = shutil.which("powershell.exe") or shutil.which("powershell")
        if powershell:
            return powershell
        return "powershell.exe"

    def _detect_version(self) -> str:
        """Query the installed PowerShell version string."""
        try:
            cmd = [
                self.ps_exe,
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                "$PSVersionTable.PSVersion.ToString()",
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=5.0)
            if res.returncode == 0 and res.stdout.strip():
                return res.stdout.strip().splitlines()[0]
        except Exception:
            pass
        return "5.1" if "WindowsPowerShell" in self.ps_exe else "Unknown"

    @property
    def is_available(self) -> bool:
        """Check if PowerShell executable exists and can run."""
        return bool(shutil.which(self.ps_exe) or os.path.exists(self.ps_exe))

    def run_command(
        self,
        command: Union[str, list[str]],
        timeout: Optional[int] = None,
        env_vars: Optional[dict[str, str]] = None,
        require_permission: bool = True,
    ) -> PowerShellCommandResult:
        """Run a command inside the workspace using PowerShell with safe parameter passing."""
        cmd_str = command if isinstance(command, str) else "& " + " ".join(f'"{c}"' for c in command)

        if require_permission:
            allowed = self.permissions.request_command_execution(cmd_str)
            if not allowed:
                return PowerShellCommandResult(
                    command=cmd_str,
                    returncode=-1,
                    stdout="",
                    stderr="Execution rejected by permission policy.",
                    duration_ms=0,
                    permitted=False,
                    powershell_exe=self.ps_exe,
                )

        t_limit = timeout or self.default_timeout
        start_time = time.time()

        env = os.environ.copy()
        if env_vars:
            env.update(env_vars)
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUNBUFFERED"] = "1"

        # Explicit controlled PowerShell invocation with safety flags
        ps_args = [
            self.ps_exe,
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            cmd_str,
        ]

        try:
            process = subprocess.run(
                ps_args,
                cwd=str(self.workspace_dir),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=t_limit,
                env=env,
            )
            duration_ms = (time.time() - start_time) * 1000
            return PowerShellCommandResult(
                command=cmd_str,
                returncode=process.returncode,
                stdout=process.stdout or "",
                stderr=process.stderr or "",
                duration_ms=duration_ms,
                timed_out=False,
                permitted=True,
                powershell_exe=self.ps_exe,
            )
        except subprocess.TimeoutExpired as exc:
            duration_ms = (time.time() - start_time) * 1000
            return PowerShellCommandResult(
                command=cmd_str,
                returncode=-1,
                stdout=exc.stdout if isinstance(exc.stdout, str) else "",
                stderr=f"Command timed out after {t_limit} seconds.",
                duration_ms=duration_ms,
                timed_out=True,
                permitted=True,
                powershell_exe=self.ps_exe,
            )
        except Exception as exc:
            duration_ms = (time.time() - start_time) * 1000
            return PowerShellCommandResult(
                command=cmd_str,
                returncode=-1,
                stdout="",
                stderr=f"Execution failed with exception: {exc}",
                duration_ms=duration_ms,
                timed_out=False,
                permitted=True,
                powershell_exe=self.ps_exe,
            )

    # -------------------------------------------------------------
    # Long-running Process & Server Management
    # -------------------------------------------------------------

    def start_background_server(
        self,
        command: str,
        name: str = "dev-server",
        detect_port_timeout: float = 6.0,
    ) -> ProcessInfo:
        """Start a development server in the background and detect its listening port."""
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUNBUFFERED"] = "1"

        ps_args = [
            self.ps_exe,
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            command,
        ]

        # Start process with pipes to capture startup logs and detect listening port
        proc = subprocess.Popen(
            ps_args,
            cwd=str(self.workspace_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
        )

        detected_port: Optional[int] = None
        start_wait = time.time()
        output_buffer = []

        # Non-blocking poll for startup lines
        while time.time() - start_wait < detect_port_timeout:
            if proc.poll() is not None:
                # Process died immediately
                err = proc.stderr.read() if proc.stderr else ""
                raise RuntimeError(f"Server process terminated immediately with code {proc.returncode}: {err}")

            # Try reading line without blocking forever
            try:
                line = proc.stdout.readline() if proc.stdout else ""
                if line:
                    output_buffer.append(line)
                    # Check for port patterns (e.g. "http://localhost:8000", "http://127.0.0.1:5173", "listening on port 3000")
                    match = re.search(r"(?:localhost|127\.0\.0\.1|port)[:\s]+(\d{4,5})", line, re.IGNORECASE)
                    if match:
                        detected_port = int(match.group(1))
                        break
            except Exception:
                pass
            time.sleep(0.3)

        info = ProcessInfo(
            pid=proc.pid,
            name=name,
            command=command,
            workspace_dir=str(self.workspace_dir),
            start_time=time.time(),
            port=detected_port,
            is_running=True,
        )

        self._record_process(info)
        return info

    def stop_process(self, pid: int) -> bool:
        """Stop a specific background process started by Electorn safely."""
        try:
            # On Windows, stop process tree via taskkill or Stop-Process
            if os.name == "nt":
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], capture_output=True, check=False)
            else:
                os.kill(pid, signal.SIGTERM)
            self._unrecord_process(pid)
            return True
        except Exception:
            return False

    def stop_all_processes(self) -> list[int]:
        """Stop all active development servers started in this workspace."""
        active = self.list_active_processes()
        stopped = []
        for p in active:
            if self.stop_process(p.pid):
                stopped.append(p.pid)
        return stopped

    def list_active_processes(self) -> list[ProcessInfo]:
        """List active processes tracked in .electorn/processes.json."""
        if not self.process_file.exists():
            return []

        try:
            data = json.loads(self.process_file.read_text(encoding="utf-8"))
            processes = [ProcessInfo(**p) for p in data]
            # Check liveness
            alive = []
            for p in processes:
                if self._is_pid_alive(p.pid):
                    alive.append(p)
            return alive
        except Exception:
            return []

    def _is_pid_alive(self, pid: int) -> bool:
        """Check if process ID is still alive."""
        if os.name == "nt":
            res = subprocess.run(["tasklist", "/FI", f"PID eq {pid}"], capture_output=True, text=True, check=False)
            return str(pid) in res.stdout
        else:
            try:
                os.kill(pid, 0)
                return True
            except OSError:
                return False

    def _record_process(self, info: ProcessInfo) -> None:
        """Save process tracking metadata to .electorn/processes.json."""
        self.process_file.parent.mkdir(parents=True, exist_ok=True)
        active = self.list_active_processes()
        active.append(info)
        self.process_file.write_text(json.dumps([p.model_dump() for p in active], indent=2), encoding="utf-8")

    def _unrecord_process(self, pid: int) -> None:
        """Remove stopped process from registry."""
        active = [p for p in self.list_active_processes() if p.pid != pid]
        if self.process_file.exists():
            self.process_file.write_text(json.dumps([p.model_dump() for p in active], indent=2), encoding="utf-8")
