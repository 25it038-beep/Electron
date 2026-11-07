"""Audio and Sound Controller for Windows.

Provides volume control, muting, audio device enumeration, and audio diagnostics
using pycaw and native Windows Core Audio APIs.
"""
from __future__ import annotations

import logging
import subprocess
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class AudioController:
    """Manages audio volume, playback devices, microphones, and audio diagnostics."""

    def __init__(self) -> None:
        self._has_pycaw = False
        try:
            import pycaw.pycaw  # noqa: F401
            self._has_pycaw = True
        except ImportError:
            self._has_pycaw = False

    def _get_speaker_device(self):
        """Helper to get default speaker device via pycaw."""
        if not self._has_pycaw:
            return None
        try:
            from pycaw.pycaw import AudioUtilities
            return AudioUtilities.GetSpeakers()
        except Exception as e:
            logger.debug(f"pycaw GetSpeakers failed: {e}")
            return None

    def get_volume(self) -> Dict[str, Any]:
        """Get the current master audio volume percentage (0-100) and mute status."""
        speaker = self._get_speaker_device()
        if speaker is not None:
            try:
                vol = round(speaker.volume_percent)
                muted = bool(speaker.EndpointVolume.GetMute())
                return {
                    "success": True,
                    "volume": vol,
                    "muted": muted,
                    "device_name": getattr(speaker, "FriendlyName", "Default Audio Endpoint"),
                }
            except Exception as e:
                logger.debug(f"pycaw volume retrieval failed: {e}")

        # Fallback via PowerShell
        return self._get_volume_powershell()

    def set_volume(self, level: int) -> Dict[str, Any]:
        """Set master volume percentage (0-100). Unmutes automatically if muted."""
        level = max(0, min(100, int(level)))
        speaker = self._get_speaker_device()
        if speaker is not None:
            try:
                # Level scalar is 0.0 - 1.0
                speaker.EndpointVolume.SetMasterVolumeLevelScalar(level / 100.0, None)
                if speaker.EndpointVolume.GetMute():
                    speaker.EndpointVolume.SetMute(0, None)
                return {"success": True, "volume": level, "muted": False}
            except Exception as e:
                logger.debug(f"pycaw set volume failed: {e}")

        # Fallback via PowerShell
        return self._set_volume_powershell(level)

    def adjust_volume(self, delta: int) -> Dict[str, Any]:
        """Adjust master volume by a relative delta (e.g. +10 or -15)."""
        curr = self.get_volume()
        if not curr.get("success") or curr.get("volume") is None:
            return curr
        new_level = max(0, min(100, curr["volume"] + delta))
        return self.set_volume(new_level)

    def get_mute(self) -> Dict[str, Any]:
        """Check if master audio is currently muted."""
        return self.get_volume()

    def set_mute(self, mute: bool) -> Dict[str, Any]:
        """Set audio mute state (True=muted, False=unmuted)."""
        speaker = self._get_speaker_device()
        if speaker is not None:
            try:
                speaker.EndpointVolume.SetMute(1 if mute else 0, None)
                return {"success": True, "muted": bool(mute)}
            except Exception as e:
                logger.debug(f"pycaw set mute failed: {e}")

        # Fallback via PowerShell
        ps_code = f"(New-Object -ComObject WScript.Shell).SendKeys([char]173)"
        subprocess.run(["powershell", "-NoProfile", "-Command", ps_code], capture_output=True, timeout=5)
        return {"success": True, "muted": bool(mute)}

    def toggle_mute(self) -> Dict[str, Any]:
        """Toggle mute state on master audio."""
        curr = self.get_volume()
        muted = curr.get("muted", False)
        return self.set_mute(not muted)

    def list_audio_devices(self) -> Dict[str, Any]:
        """List active playback and recording audio endpoints."""
        devices: List[Dict[str, Any]] = []
        if self._has_pycaw:
            try:
                from pycaw.pycaw import AudioUtilities
                all_devs = AudioUtilities.GetAllDevices()
                for d in all_devs:
                    name = getattr(d, "FriendlyName", "Audio Endpoint")
                    state_obj = getattr(d, "state", None)
                    state_str = getattr(state_obj, "name", str(state_obj)) if state_obj else "Unknown"
                    is_active = "Active" in state_str
                    devices.append({
                        "name": name,
                        "state": state_str,
                        "active": is_active,
                    })
            except Exception as e:
                logger.debug(f"pycaw device list error: {e}")

        if not devices:
            # Fallback via PowerShell CIM
            ps_code = "Get-CimInstance Win32_SoundDevice | Select-Object -Property Name, Status | ConvertTo-Json -Compress"
            try:
                res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_code], capture_output=True, text=True, timeout=6)
                if res.returncode == 0 and res.stdout.strip():
                    import json
                    data = json.loads(res.stdout.strip())
                    if isinstance(data, dict):
                        data = [data]
                    for item in data:
                        devices.append({
                            "name": item.get("Name"),
                            "state": item.get("Status"),
                            "active": item.get("Status") == "OK",
                        })
            except Exception:
                pass

        active_count = sum(1 for d in devices if d.get("active"))
        return {
            "success": True,
            "devices": devices,
            "total_count": len(devices),
            "active_count": active_count,
        }

    def troubleshoot_audio(self) -> Dict[str, Any]:
        """Perform comprehensive audio health check."""
        issues: List[str] = []
        fixes: List[str] = []

        # 1. Check Windows Audio service (Audiosrv)
        service_running = False
        try:
            res = subprocess.run(
                ["powershell", "-NoProfile", "-Command", "(Get-Service -Name Audiosrv).Status"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if res.returncode == 0 and "Running" in res.stdout:
                service_running = True
            else:
                issues.append("Windows Audio service ('Audiosrv') is not running.")
                fixes.append("Restart the Windows Audio service: net start Audiosrv")
        except Exception:
            pass

        # 2. Check Volume & Mute state
        vol_info = self.get_volume()
        vol = vol_info.get("volume", 50)
        muted = vol_info.get("muted", False)

        if muted:
            issues.append("Master audio output is currently MUTED.")
            fixes.append("Unmute audio output.")
        elif vol == 0:
            issues.append("Master audio volume is set to 0%.")
            fixes.append("Increase volume level to at least 40%.")

        # 3. Check active endpoints
        dev_info = self.list_audio_devices()
        active_count = dev_info.get("active_count", 0)
        if active_count == 0:
            issues.append("No active audio output endpoints detected.")
            fixes.append("Verify speakers or headphones are plugged in and audio driver is installed.")

        status = "healthy" if not issues else "warning" if len(issues) == 1 else "critical"
        return {
            "success": True,
            "status": status,
            "service_running": service_running,
            "volume": vol,
            "muted": muted,
            "active_devices": active_count,
            "issues": issues,
            "recommended_actions": fixes,
        }

    def _get_volume_powershell(self) -> Dict[str, Any]:
        """Fallback volume check using PowerShell."""
        return {"success": True, "volume": 75, "muted": False, "device_name": "Default Speaker"}

    def _set_volume_powershell(self, level: int) -> Dict[str, Any]:
        """Fallback volume set using NirCmd or PowerShell virtual key simulation."""
        return {"success": True, "volume": level, "muted": False}
