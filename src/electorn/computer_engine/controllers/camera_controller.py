"""Camera and Webcam Controller for Windows.

Provides device enumeration, camera driver status, and hardware diagnostic checks
for integrated and USB webcams.
"""
from __future__ import annotations

import logging
import subprocess
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class CameraController:
    """Manages camera detection, hardware status, and diagnostics."""

    def list_cameras(self) -> Dict[str, Any]:
        """List all integrated and external cameras detected by Windows PnP."""
        ps_code = (
            "Get-PnpDevice -Class Camera -ErrorAction SilentlyContinue | "
            "Select-Object -Property FriendlyName, Status, Present, InstanceId | ConvertTo-Json -Compress"
        )
        cameras: List[Dict[str, Any]] = []
        try:
            res = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_code],
                capture_output=True,
                text=True,
                timeout=6,
            )
            if res.returncode == 0 and res.stdout.strip():
                import json
                data = json.loads(res.stdout.strip())
                if isinstance(data, dict):
                    data = [data]
                for item in data:
                    cameras.append({
                        "name": item.get("FriendlyName"),
                        "status": item.get("Status"),
                        "present": item.get("Present", True),
                        "instance_id": item.get("InstanceId"),
                    })
        except Exception as e:
            logger.debug(f"Camera query error: {e}")

        # Check if any camera is OK and present
        active_cameras = [c for c in cameras if c.get("status") == "OK" and c.get("present")]

        return {
            "success": True,
            "cameras": cameras,
            "total_count": len(cameras),
            "available_count": len(active_cameras),
            "primary_camera": active_cameras[0]["name"] if active_cameras else None,
        }

    def check_camera_health(self) -> Dict[str, Any]:
        """Diagnose camera subsystem health, driver state, and service availability."""
        cam_info = self.list_cameras()
        issues: List[str] = []
        fixes: List[str] = []

        if cam_info.get("available_count", 0) == 0:
            issues.append("No active or working camera hardware detected.")
            fixes.append("Check physical camera shutter switch, USB connection, or device manager drivers.")

        # Check Windows Camera Frame Server service (FrameServer)
        frame_server_ok = True
        try:
            res = subprocess.run(
                ["powershell", "-NoProfile", "-Command", "(Get-Service -Name FrameServer -ErrorAction SilentlyContinue).Status"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            # FrameServer is often on-demand (Manual), so Stopped is not necessarily an error unless disabled
            status = res.stdout.strip()
            if status == "Disabled":
                frame_server_ok = False
                issues.append("Windows Camera Frame Server service is disabled.")
                fixes.append("Enable FrameServer service in services.msc.")
        except Exception:
            pass

        return {
            "success": True,
            "healthy": len(issues) == 0,
            "cameras_found": cam_info.get("available_count", 0),
            "primary_camera": cam_info.get("primary_camera"),
            "issues": issues,
            "recommended_actions": fixes,
        }
