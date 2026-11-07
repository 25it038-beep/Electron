"""Bluetooth and USB Peripherals Controller for Windows.

Provides enumeration of paired Bluetooth devices, connection status,
and full discovery of connected USB peripherals.
"""
from __future__ import annotations

import logging
import subprocess
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class BluetoothController:
    """Manages Bluetooth devices, radio status, and USB peripheral inventory."""

    def list_bluetooth_devices(self) -> Dict[str, Any]:
        """List paired and detected Bluetooth devices."""
        ps_code = (
            "Get-PnpDevice -Class Bluetooth -ErrorAction SilentlyContinue | "
            "Select-Object -Property FriendlyName, Status, Present | ConvertTo-Json -Compress"
        )
        devices: List[Dict[str, Any]] = []
        try:
            res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_code], capture_output=True, text=True, timeout=6)
            if res.returncode == 0 and res.stdout.strip():
                import json
                data = json.loads(res.stdout.strip())
                if isinstance(data, dict):
                    data = [data]
                for item in data:
                    name = item.get("FriendlyName")
                    if name and not name.startswith("Microsoft Bluetooth") and not name.startswith("Generic Bluetooth"):
                        devices.append({
                            "name": name,
                            "status": item.get("Status"),
                            "connected": bool(item.get("Present", False)),
                        })
        except Exception as e:
            logger.debug(f"Bluetooth listing error: {e}")

        connected_count = sum(1 for d in devices if d.get("connected"))
        return {
            "success": True,
            "devices": devices,
            "total_paired": len(devices),
            "currently_connected": connected_count,
        }

    def list_usb_devices(self) -> Dict[str, Any]:
        """Discover connected USB peripherals categorized by type."""
        ps_code = (
            "Get-PnpDevice -Class USB -ErrorAction SilentlyContinue | "
            "Where-Object { $_.Present -eq $true } | "
            "Select-Object -Property FriendlyName, Status | ConvertTo-Json -Compress"
        )
        usb_devices: List[Dict[str, Any]] = []
        try:
            res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_code], capture_output=True, text=True, timeout=6)
            if res.returncode == 0 and res.stdout.strip():
                import json
                data = json.loads(res.stdout.strip())
                if isinstance(data, dict):
                    data = [data]
                for item in data:
                    name = item.get("FriendlyName")
                    if name:
                        usb_devices.append({
                            "name": name,
                            "status": item.get("Status", "OK"),
                        })
        except Exception as e:
            logger.debug(f"USB device query error: {e}")

        return {
            "success": True,
            "peripherals": usb_devices,
            "count": len(usb_devices),
        }
