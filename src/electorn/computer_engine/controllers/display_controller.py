"""Display and Graphics Controller for Windows.

Provides monitor querying, brightness control, resolution checks, and
real-time NVIDIA GPU telemetry using native Windows APIs and nvidia-smi.
"""
from __future__ import annotations

import logging
import os
import shutil
import subprocess
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class DisplayController:
    """Manages displays, brightness, screen configurations, and NVIDIA GPU metrics."""

    def __init__(self) -> None:
        self.has_nvidia_smi = shutil.which("nvidia-smi") is not None

    def get_brightness(self) -> Dict[str, Any]:
        """Get the current screen brightness level (0-100) via WMI/CIM."""
        cmd = [
            "powershell",
            "-NoProfile",
            "-Command",
            "(Get-CimInstance -Namespace root/wmi -ClassName WmiMonitorBrightness -ErrorAction SilentlyContinue).CurrentBrightness",
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            if res.returncode == 0 and res.stdout.strip():
                val = int(res.stdout.strip().split()[-1])
                return {"success": True, "brightness": val, "supported": True}
        except Exception as e:
            logger.debug(f"Brightness query error: {e}")

        return {"success": False, "brightness": None, "supported": False, "error": "Brightness control not supported on this display"}

    def set_brightness(self, level: int) -> Dict[str, Any]:
        """Set the screen brightness level (0-100)."""
        level = max(0, min(100, int(level)))
        ps_code = (
            f"$m = Get-CimInstance -Namespace root/wmi -ClassName WmiMonitorBrightnessMethods -ErrorAction SilentlyContinue; "
            f"if ($m) {{ Invoke-CimMethod -InputObject $m -MethodName WmiSetBrightness -Arguments @{{Timeout = 1; Brightness = {level}}} }}"
        )
        try:
            res = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_code],
                capture_output=True,
                text=True,
                timeout=6,
            )
            if res.returncode == 0:
                return {"success": True, "brightness": level}
            return {"success": False, "error": res.stderr.strip() or "Failed to set brightness"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def adjust_brightness(self, delta: int) -> Dict[str, Any]:
        """Adjust current brightness by a relative delta (e.g. +10 or -10)."""
        curr = self.get_brightness()
        if not curr.get("success") or curr.get("brightness") is None:
            return curr
        new_val = max(0, min(100, curr["brightness"] + delta))
        return self.set_brightness(new_val)

    def get_display_info(self) -> Dict[str, Any]:
        """Retrieve multi-monitor setup, resolutions, and refresh rates."""
        ps_code = (
            "Get-CimInstance Win32_VideoController | Select-Object -Property Name, CurrentHorizontalResolution, "
            "CurrentVerticalResolution, CurrentRefreshRate | ConvertTo-Json -Compress"
        )
        displays: List[Dict[str, Any]] = []
        try:
            res = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_code],
                capture_output=True,
                text=True,
                timeout=8,
            )
            if res.returncode == 0 and res.stdout.strip():
                import json
                data = json.loads(res.stdout.strip())
                if isinstance(data, dict):
                    data = [data]
                for item in data:
                    displays.append({
                        "name": item.get("Name"),
                        "width": item.get("CurrentHorizontalResolution"),
                        "height": item.get("CurrentVerticalResolution"),
                        "refresh_rate": item.get("CurrentRefreshRate"),
                    })
        except Exception as e:
            logger.debug(f"Display info query error: {e}")

        # Fallback / primary resolution via pyautogui if available
        primary_res = None
        try:
            import pyautogui
            w, h = pyautogui.size()
            primary_res = {"width": w, "height": h}
        except Exception:
            pass

        return {
            "success": True,
            "primary_resolution": primary_res,
            "controllers": displays,
            "count": len(displays),
        }

    def get_gpu_info(self) -> Dict[str, Any]:
        """Retrieve real-time NVIDIA GPU telemetry and active compute processes."""
        if not self.has_nvidia_smi:
            return {
                "success": False,
                "has_nvidia": False,
                "message": "NVIDIA GPU management tool (nvidia-smi) not found in system PATH",
            }

        telemetry_cmd = [
            "nvidia-smi",
            "--query-gpu=index,name,utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw,driver_version",
            "--format=csv,noheader,nounits",
        ]
        gpus: List[Dict[str, Any]] = []
        try:
            res = subprocess.run(telemetry_cmd, capture_output=True, text=True, timeout=5)
            if res.returncode == 0:
                for line in res.stdout.strip().splitlines():
                    parts = [p.strip() for p in line.split(",")]
                    if len(parts) >= 8:
                        try:
                            gpus.append({
                                "index": int(parts[0]),
                                "name": parts[1],
                                "utilization_percent": float(parts[2]),
                                "memory_used_mb": float(parts[3]),
                                "memory_total_mb": float(parts[4]),
                                "temperature_c": float(parts[5]),
                                "power_draw_w": float(parts[6]),
                                "driver_version": parts[7],
                            })
                        except ValueError:
                            continue
        except Exception as e:
            logger.debug(f"nvidia-smi telemetry error: {e}")

        # Query compute processes
        processes: List[Dict[str, Any]] = []
        proc_cmd = [
            "nvidia-smi",
            "--query-compute-apps=pid,process_name,used_memory",
            "--format=csv,noheader,nounits",
        ]
        try:
            res_proc = subprocess.run(proc_cmd, capture_output=True, text=True, timeout=5)
            if res_proc.returncode == 0 and res_proc.stdout.strip():
                for line in res_proc.stdout.strip().splitlines():
                    parts = [p.strip() for p in line.split(",")]
                    if len(parts) >= 2:
                        processes.append({
                            "pid": parts[0],
                            "process_name": parts[1],
                            "used_memory_mb": parts[2] if len(parts) > 2 else "N/A",
                        })
        except Exception:
            pass

        return {
            "success": True,
            "has_nvidia": len(gpus) > 0,
            "gpus": gpus,
            "processes": processes,
        }
