"""Low-level OS and peripheral controllers for Windows."""
from electorn.computer_engine.controllers.mouse_controller import MouseController
from electorn.computer_engine.controllers.keyboard_controller import KeyboardController
from electorn.computer_engine.controllers.clipboard_controller import ClipboardController
from electorn.computer_engine.controllers.screen_controller import ScreenController
from electorn.computer_engine.controllers.window_controller import WindowController
from electorn.computer_engine.controllers.display_controller import DisplayController
from electorn.computer_engine.controllers.audio_controller import AudioController
from electorn.computer_engine.controllers.camera_controller import CameraController
from electorn.computer_engine.controllers.network_controller import NetworkController
from electorn.computer_engine.controllers.bluetooth_controller import BluetoothController
from electorn.computer_engine.controllers.storage_controller import StorageController
from electorn.computer_engine.controllers.power_controller import PowerController
from electorn.computer_engine.controllers.system_admin import SystemAdminController
from electorn.computer_engine.controllers.troubleshooter import DeviceTroubleshooter
from electorn.computer_engine.controllers.device_inventory import DeviceInventory

__all__ = [
    "MouseController",
    "KeyboardController",
    "ClipboardController",
    "ScreenController",
    "WindowController",
    "DisplayController",
    "AudioController",
    "CameraController",
    "NetworkController",
    "BluetoothController",
    "StorageController",
    "PowerController",
    "SystemAdminController",
    "DeviceTroubleshooter",
    "DeviceInventory",
]
