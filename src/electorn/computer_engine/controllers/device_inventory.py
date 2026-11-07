"""Unified Device & Hardware Inventory Catalog for Windows.

Aggregates OS version, CPU, GPU, RAM, Storage, Displays, Audio endpoints,
and Network hardware into a single comprehensive diagnostic snapshot.
"""
from __future__ import annotations

import logging
import platform
from typing import Any, Dict

import psutil

from electorn.computer_engine.controllers.audio_controller import AudioController
from electorn.computer_engine.controllers.bluetooth_controller import BluetoothController
from electorn.computer_engine.controllers.camera_controller import CameraController
from electorn.computer_engine.controllers.display_controller import DisplayController
from electorn.computer_engine.controllers.network_controller import NetworkController
from electorn.computer_engine.controllers.power_controller import PowerController
from electorn.computer_engine.controllers.storage_controller import StorageController

logger = logging.getLogger(__name__)


class DeviceInventory:
    """Aggregates all hardware components into a single structured queryable object."""

    def __init__(self) -> None:
        self.display = DisplayController()
        self.audio = AudioController()
        self.camera = CameraController()
        self.network = NetworkController()
        self.bluetooth = BluetoothController()
        self.storage = StorageController()
        self.power = PowerController()

    def get_full_inventory(self) -> Dict[str, Any]:
        """Generate a complete hardware and system inventory."""
        mem = psutil.virtual_memory()

        # OS Details
        os_info = {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "architecture": platform.machine(),
            "processor": platform.processor(),
        }

        # CPU Details
        cpu_info = {
            "physical_cores": psutil.cpu_count(logical=False),
            "logical_cores": psutil.cpu_count(logical=True),
            "current_frequency_mhz": getattr(psutil.cpu_freq(), "current", None) if psutil.cpu_freq() else None,
        }

        # Memory Details
        memory_info = {
            "total_gb": round(mem.total / (1024**3), 2),
            "available_gb": round(mem.available / (1024**3), 2),
            "percent_used": mem.percent,
        }

        # GPU Details
        gpu_info = self.display.get_gpu_info()

        # Displays
        display_info = self.display.get_display_info()

        # Audio
        audio_info = self.audio.get_volume()

        # Camera
        camera_info = self.camera.list_cameras()

        # Network
        wifi_info = self.network.get_wifi_status()

        # Power / Battery
        battery_info = self.power.get_battery_status()

        # Storage
        storage_info = self.storage.get_drive_overview()

        # Peripherals
        usb_info = self.bluetooth.list_usb_devices()

        return {
            "success": True,
            "os": os_info,
            "cpu": cpu_info,
            "memory": memory_info,
            "gpu": gpu_info,
            "display": display_info,
            "audio": audio_info,
            "camera": camera_info,
            "network": wifi_info,
            "battery": battery_info,
            "storage": storage_info,
            "peripherals": usb_info,
        }
