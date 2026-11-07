"""Power, Battery, and Session Controller for Windows.

Provides sleep, workstation lock, hibernate, power plan configuration,
battery telemetry, and safe confirmation-gated shutdown/restart.
"""
from __future__ import annotations

import logging
import subprocess
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class PowerController:
    """Manages workstation power state, power plans, and battery health."""

    def lock_workstation(self) -> Dict[str, Any]:
        """Instantly lock the Windows workstation session."""
        try:
            res = subprocess.run(["rundll32.exe", "user32.dll,LockWorkStation"], capture_output=True, timeout=5)
            return {"success": res.returncode == 0, "action": "lock"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def sleep(self) -> Dict[str, Any]:
        """Put the computer into suspend / sleep mode."""
        try:
            res = subprocess.run(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"], capture_output=True, timeout=5)
            return {"success": res.returncode == 0, "action": "sleep"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def hibernate(self) -> Dict[str, Any]:
        """Hibernate the computer."""
        try:
            res = subprocess.run(["shutdown", "/h"], capture_output=True, timeout=5)
            return {"success": res.returncode == 0, "action": "hibernate"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def shutdown(self, confirm: bool = False, delay_seconds: int = 30) -> Dict[str, Any]:
        """Shut down the computer. Strictly requires explicit confirmation to prevent accidental shutdowns."""
        if not confirm:
            return {
                "success": False,
                "requires_confirmation": True,
                "message": "Shutdown aborted. Explicit confirmation is required to turn off the computer.",
            }
        try:
            cmd = ["shutdown", "/s", "/t", str(delay_seconds), "/c", "Aria scheduled system shutdown."]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            return {"success": res.returncode == 0, "action": "shutdown", "delay_seconds": delay_seconds}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def restart(self, confirm: bool = False, delay_seconds: int = 30) -> Dict[str, Any]:
        """Restart the computer. Strictly requires explicit confirmation."""
        if not confirm:
            return {
                "success": False,
                "requires_confirmation": True,
                "message": "Restart aborted. Explicit confirmation is required to restart the computer.",
            }
        try:
            cmd = ["shutdown", "/r", "/t", str(delay_seconds), "/c", "Aria scheduled system restart."]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            return {"success": res.returncode == 0, "action": "restart", "delay_seconds": delay_seconds}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def cancel_shutdown(self) -> Dict[str, Any]:
        """Cancel a pending scheduled shutdown or restart."""
        try:
            res = subprocess.run(["shutdown", "/a"], capture_output=True, text=True, timeout=5)
            return {"success": res.returncode == 0, "message": "Pending shutdown cancelled."}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_battery_status(self) -> Dict[str, Any]:
        """Retrieve real-time battery charge, charging state, and estimated runtime."""
        import psutil

        battery = psutil.sensors_battery()
        if battery is None:
            return {
                "success": True,
                "has_battery": False,
                "message": "No battery detected (Desktop system or AC direct)",
            }

        secs = battery.secsleft
        time_left_str = "Unlimited (Plugged In)" if battery.power_plugged else (
            f"{secs // 3600}h {(secs % 3600) // 60}m" if secs > 0 else "Calculating..."
        )

        return {
            "success": True,
            "has_battery": True,
            "percent": battery.percent,
            "power_plugged": battery.power_plugged,
            "charging": battery.power_plugged and battery.percent < 100,
            "time_remaining": time_left_str,
            "low_battery_warning": (not battery.power_plugged) and battery.percent <= 20,
        }

    def get_power_scheme(self) -> Dict[str, Any]:
        """Get the active Windows power plan scheme."""
        try:
            res = subprocess.run(["powercfg", "/getactivescheme"], capture_output=True, text=True, timeout=5)
            if res.returncode == 0 and res.stdout:
                line = res.stdout.strip()
                return {"success": True, "active_scheme": line}
        except Exception as e:
            logger.debug(f"Powercfg query error: {e}")
        return {"success": False, "active_scheme": "Balanced"}

    def set_power_scheme(self, mode: str) -> Dict[str, Any]:
        """Set power plan mode: 'balanced', 'high_performance', or 'power_saver'."""
        mode_lower = mode.lower()
        # Standard well-known Windows Power Scheme GUIDs
        scheme_guids = {
            "balanced": "381b4222-f694-41f0-9685-ff5bb260df2e",
            "high_performance": "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c",
            "power_saver": "a1841308-3541-4fab-bc81-f71556f20b4a",
        }
        guid = scheme_guids.get(mode_lower)
        if not guid:
            return {"success": False, "error": f"Unknown mode: {mode}. Use 'balanced', 'high_performance', or 'power_saver'."}

        try:
            res = subprocess.run(["powercfg", "/setactive", guid], capture_output=True, timeout=5)
            return {"success": res.returncode == 0, "mode": mode_lower, "guid": guid}
        except Exception as e:
            return {"success": False, "error": str(e)}
