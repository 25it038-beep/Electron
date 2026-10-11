"""Detects available developer tools, runtimes, and system capabilities."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
from pydantic import BaseModel, Field


class ToolEnvironment(BaseModel):
    """Audit of host machine development runtimes."""

    os_system: str
    os_release: str
    architecture: str
    python_version: str
    has_git: bool = False
    has_node: bool = False
    node_version: str = ""
    has_npm: bool = False
    has_docker: bool = False
    has_bun: bool = False
    has_ollama: bool = False
    ollama_running: bool = False
    has_powershell: bool = False
    powershell_version: str = ""


class EnvironmentDetector:
    """Probes the host operating system and developer toolchains."""

    @staticmethod
    def _run_tool_version(cmd: list[str]) -> tuple[bool, str]:
        """Run tool --version safely returning (installed, version_str)."""
        executable = shutil.which(cmd[0])
        if not executable:
            return False, ""
        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=2.0,
                check=False,
            )
            out = (res.stdout or res.stderr).strip().splitlines()
            ver = out[0] if out else ""
            return res.returncode == 0, ver
        except Exception:
            return False, ""

    @classmethod
    def detect(cls) -> ToolEnvironment:
        """Inspect host platform and installed CLI developer tools."""
        has_node, node_ver = cls._run_tool_version(["node", "--version"])
        has_npm, _ = cls._run_tool_version(["npm", "--version"])
        has_git, _ = cls._run_tool_version(["git", "--version"])
        has_docker, _ = cls._run_tool_version(["docker", "--version"])
        has_bun, _ = cls._run_tool_version(["bun", "--version"])
        has_ollama, _ = cls._run_tool_version(["ollama", "--version"])

        # Detect PowerShell
        has_pwsh, pwsh_ver = cls._run_tool_version(["pwsh", "--version"])
        if not has_pwsh:
            has_ps, _ = cls._run_tool_version(["powershell", "-NoProfile", "-Command", "$PSVersionTable.PSVersion.Major"])
            has_powershell = has_ps
            powershell_version = "5.1 (Windows PowerShell)" if has_ps else ""
        else:
            has_powershell = True
            powershell_version = pwsh_ver or "PowerShell Core"

        return ToolEnvironment(
            os_system=platform.system(),
            os_release=platform.release(),
            architecture=platform.machine(),
            python_version=platform.python_version(),
            has_git=has_git,
            has_node=has_node,
            node_version=node_ver,
            has_npm=has_npm,
            has_docker=has_docker,
            has_bun=has_bun,
            has_ollama=has_ollama,
            has_powershell=has_powershell,
            powershell_version=powershell_version,
        )
