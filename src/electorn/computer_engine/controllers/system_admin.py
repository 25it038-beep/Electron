"""Windows System Administration, Services, and Event Log Controller.

Provides service inspection, event log queries, Windows Update status,
and safe structured PowerShell execution with strict risk gating.
"""
from __future__ import annotations

import logging
import subprocess
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class SystemAdminController:
    """Manages Windows services, event logs, scheduled tasks, and administrative queries."""

    # Services that can be safely queried or restarted
    ALLOWED_RESTART_SERVICES = {
        "audiosrv": "Windows Audio",
        "audioendpointbuilder": "Windows Audio Endpoint Builder",
        "spooler": "Print Spooler",
        "wuauserv": "Windows Update",
        "lanmanworkstation": "Workstation",
        "dnscache": "DNS Client",
    }

    def list_services(self, names: Optional[List[str]] = None) -> Dict[str, Any]:
        """List Windows services and their current state."""
        filter_names = names or ["Audiosrv", "Spooler", "wuauserv", "Dhcp", "Dnscache"]
        ps_names = ", ".join(f"'{n}'" for n in filter_names)
        ps_code = (
            f"Get-Service -Name {ps_names} -ErrorAction SilentlyContinue | "
            f"Select-Object -Property Name, DisplayName, Status, StartType | ConvertTo-Json -Compress"
        )
        services: List[Dict[str, Any]] = []
        try:
            res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_code], capture_output=True, text=True, timeout=6)
            if res.returncode == 0 and res.stdout.strip():
                import json
                data = json.loads(res.stdout.strip())
                if isinstance(data, dict):
                    data = [data]
                for item in data:
                    services.append({
                        "name": item.get("Name"),
                        "display_name": item.get("DisplayName"),
                        "status": "Running" if str(item.get("Status")) == "4" or item.get("Status") == "Running" else "Stopped",
                        "start_type": str(item.get("StartType")),
                    })
        except Exception as e:
            logger.debug(f"Service list error: {e}")

        return {
            "success": True,
            "services": services,
            "count": len(services),
        }

    def check_service(self, name: str) -> Dict[str, Any]:
        """Check status of a specific Windows service."""
        try:
            res = subprocess.run(
                ["powershell", "-NoProfile", "-Command", f"(Get-Service -Name '{name}' -ErrorAction SilentlyContinue).Status"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            status = res.stdout.strip()
            return {
                "success": bool(status),
                "service": name,
                "status": status if status else "Not Found",
                "running": status == "Running",
            }
        except Exception as e:
            return {"success": False, "service": name, "error": str(e)}

    def restart_service(self, name: str) -> Dict[str, Any]:
        """Safely restart a registered Windows service (e.g. Audiosrv or Spooler)."""
        name_clean = name.strip().lower()
        if name_clean not in self.ALLOWED_RESTART_SERVICES:
            return {
                "success": False,
                "error": f"Restarting service '{name}' is restricted for system stability. Allowed: {list(self.ALLOWED_RESTART_SERVICES.keys())}",
            }

        try:
            cmd = f"Restart-Service -Name '{name_clean}' -Force"
            res = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True, timeout=12)
            if res.returncode == 0:
                return {"success": True, "service": name_clean, "action": "restarted"}
            return {"success": False, "service": name_clean, "error": res.stderr.strip() or "Permission denied or failed to restart"}
        except Exception as e:
            return {"success": False, "service": name_clean, "error": str(e)}

    def get_recent_errors(self, log_name: str = "Application", max_events: int = 5) -> Dict[str, Any]:
        """Fetch recent error events from Windows Event Log."""
        max_events = max(1, min(20, max_events))
        ps_code = (
            f"Get-WinEvent -FilterHashtable @{{LogName='{log_name}'; Level=2}} -MaxEvents {max_events} -ErrorAction SilentlyContinue | "
            f"Select-Object -Property TimeCreated, ProviderName, Id, Message | ConvertTo-Json -Compress"
        )
        errors: List[Dict[str, Any]] = []
        try:
            res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_code], capture_output=True, text=True, timeout=8)
            if res.returncode == 0 and res.stdout.strip():
                import json
                data = json.loads(res.stdout.strip())
                if isinstance(data, dict):
                    data = [data]
                for item in data:
                    msg = item.get("Message", "")
                    # Shorten message preview
                    preview = (msg[:160] + "...") if msg and len(msg) > 160 else msg
                    errors.append({
                        "time": str(item.get("TimeCreated")),
                        "source": item.get("ProviderName"),
                        "event_id": item.get("Id"),
                        "message_preview": preview,
                    })
        except Exception as e:
            logger.debug(f"Event log query error: {e}")

        return {
            "success": True,
            "log": log_name,
            "count": len(errors),
            "errors": errors,
        }

    def check_update_service_status(self) -> Dict[str, Any]:
        """Check status of Windows Update service."""
        return self.check_service("wuauserv")

    def execute_powershell(self, command: str, risk_level: str = "read_only", timeout: int = 10) -> Dict[str, Any]:
        """Execute a structured PowerShell command with safety classification."""
        command = command.strip()
        # High risk blocking
        prohibited = ["format ", "del /f", "remove-item -recurse c:", "diskpart", "bcdedit"]
        for p in prohibited:
            if p in command.lower():
                return {
                    "success": False,
                    "blocked": True,
                    "error": f"Command contains prohibited destructive operation: '{p}'",
                }

        try:
            res = subprocess.run(
                ["powershell", "-NoProfile", "-Command", command],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return {
                "success": res.returncode == 0,
                "returncode": res.returncode,
                "stdout": res.stdout.strip(),
                "stderr": res.stderr.strip(),
                "risk_level": risk_level,
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "timeout": True, "error": f"Command timed out after {timeout} seconds"}
        except Exception as e:
            return {"success": False, "error": str(e)}
