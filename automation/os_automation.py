"""Dedicated Windows OS Automation Engine for Electorn AI.

Handles application lifecycles, pywinauto UI automation, window management,
keyboard/mouse control, and system diagnostics.
"""

from __future__ import annotations

import ctypes
import os
import pathlib
import platform
import subprocess
import sys
import time
from typing import Any, Optional

try:
    import psutil
    PSUTIL_AVAILABLE = True
except Exception:
    PSUTIL_AVAILABLE = False

try:
    import pyautogui
    pyautogui.FAILSAFE = True
    PYAUTOGUI_AVAILABLE = True
except Exception:
    PYAUTOGUI_AVAILABLE = False

try:
    import pyperclip
    PYPERCLIP_AVAILABLE = True
except Exception:
    PYPERCLIP_AVAILABLE = False

try:
    import pywinauto
    PYWINAUTO_AVAILABLE = True
except Exception:
    PYWINAUTO_AVAILABLE = False


class WindowsOSAutomation:
    """Controls native Windows applications, UI controls, windows, and hardware."""

    # Map of recognizable friendly names to executables
    APP_REGISTRY: dict[str, list[str]] = {
        "notepad": ["notepad.exe"],
        "notes": ["notepad.exe"],
        "calc": ["calc.exe"],
        "calculator": ["calc.exe"],
        "explorer": ["explorer.exe"],
        "files": ["explorer.exe"],
        "file explorer": ["explorer.exe"],
        "terminal": ["wt.exe", "powershell.exe", "cmd.exe"],
        "powershell": ["powershell.exe"],
        "cmd": ["cmd.exe"],
        "command prompt": ["cmd.exe"],
        "vscode": ["code.cmd", "code.exe"],
        "vs code": ["code.cmd", "code.exe"],
        "code": ["code.cmd", "code.exe"],
        "paint": ["mspaint.exe"],
        "task manager": ["taskmgr.exe"],
        "taskmgr": ["taskmgr.exe"],
        "settings": ["control.exe"],
        "control panel": ["control.exe"],
        "spotify": ["spotify.exe"],
        "chrome": ["chrome.exe"],
        "edge": ["msedge.exe"],
    }

    def __init__(self) -> None:
        self.last_launched_process: Optional[subprocess.Popen] = None

    # =========================================================================
    # APPLICATION CONTROLS
    # =========================================================================

    def launch_app(self, app_name: str, wait_seconds: float = 2.0) -> dict[str, Any]:
        """Launch an installed desktop application and verify readiness."""
        clean_name = app_name.strip().lower()
        executables = self.APP_REGISTRY.get(clean_name, [clean_name])

        launched_exe = None
        for exe in executables:
            try:
                if sys.platform == "win32":
                    proc = subprocess.Popen(exe, shell=True)
                else:
                    proc = subprocess.Popen([exe])
                self.last_launched_process = proc
                launched_exe = exe
                break
            except Exception:
                continue

        if not launched_exe:
            return {
                "success": False,
                "app": app_name,
                "message": f"Could not find or launch executable for '{app_name}'.",
            }

        # Wait for application process / window to become ready
        time.sleep(wait_seconds)
        is_running = self.is_app_running(clean_name)

        return {
            "success": True,
            "app": app_name,
            "executable": launched_exe,
            "verified_running": is_running,
            "message": f"Launched {app_name.capitalize()} successfully.",
        }

    def close_app(self, app_name: str, force: bool = False) -> dict[str, Any]:
        """Safely close an application by name or process."""
        clean_name = app_name.strip().lower()
        proc_name_map = {
            "notepad": "notepad.exe",
            "calculator": "CalculatorApp.exe",
            "calc": "CalculatorApp.exe",
            "paint": "mspaint.exe",
            "cmd": "cmd.exe",
            "terminal": "WindowsTerminal.exe",
            "chrome": "chrome.exe",
            "edge": "msedge.exe",
            "spotify": "Spotify.exe",
        }
        target_proc = proc_name_map.get(clean_name, f"{clean_name}.exe")

        if sys.platform == "win32":
            flag = "/f" if force else ""
            cmd = ["taskkill", "/im", target_proc]
            if force:
                cmd.insert(1, "/f")
            res = subprocess.run(cmd, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            success = res.returncode == 0
        else:
            cmd = ["pkill", "-f", clean_name]
            res = subprocess.run(cmd, check=False)
            success = res.returncode == 0

        return {
            "success": success,
            "app": app_name,
            "message": f"Closed application {app_name}." if success else f"No running instance of {app_name} found.",
        }

    def is_app_running(self, app_name: str) -> bool:
        """Inspect if an application process is active."""
        if not PSUTIL_AVAILABLE:
            return True  # Fallback optimistic
        clean = app_name.strip().lower()
        for p in psutil.process_iter(["name"]):
            try:
                name = (p.info["name"] or "").lower()
                if clean in name:
                    return True
            except Exception:
                continue
        return False

    def list_open_windows(self) -> list[str]:
        """Inspect available desktop windows and their titles."""
        windows = []
        if PYWINAUTO_AVAILABLE and sys.platform == "win32":
            try:
                from pywinauto import Desktop
                d = Desktop(backend="uia")
                for w in d.windows():
                    title = w.window_text()
                    if title and title.strip():
                        windows.append(title.strip())
            except Exception:
                pass

        if not windows and sys.platform == "win32":
            # Fallback to PowerShell Get-Process with MainWindowTitle
            try:
                res = subprocess.run(
                    ["powershell", "-NoProfile", "-Command", "Get-Process | Where-Object {$_.MainWindowTitle} | Select-Object -ExpandProperty MainWindowTitle"],
                    capture_output=True, text=True, check=False, timeout=5,
                )
                if res.stdout:
                    windows = [w.strip() for w in res.stdout.splitlines() if w.strip()]
            except Exception:
                pass
        return windows

    # =========================================================================
    # WINDOW MANAGEMENT
    # =========================================================================

    def minimize_all_windows(self) -> str:
        """Minimize all open windows and show the desktop."""
        if PYAUTOGUI_AVAILABLE:
            pyautogui.hotkey("win", "d")
            return "Minimized all open windows."
        if sys.platform == "win32":
            try:
                import win32com.client
                shell = win32com.client.Dispatch("Shell.Application")
                shell.MinimizeAll()
                return "Minimized all open windows."
            except Exception as err:
                return f"Failed to minimize windows: {err}"
        return "Window control not supported on this platform."

    def maximize_window(self) -> str:
        """Maximize the currently active window."""
        if PYAUTOGUI_AVAILABLE:
            pyautogui.hotkey("win", "up")
            return "Maximized active window."
        return "Window maximize unavailable."

    def switch_window(self) -> str:
        """Switch to the next window (Alt + Tab)."""
        if PYAUTOGUI_AVAILABLE:
            pyautogui.hotkey("alt", "tab")
            return "Switched active window."
        return "Window switch unavailable."

    def close_active_window(self) -> str:
        """Close the currently focused window (Alt + F4)."""
        if PYAUTOGUI_AVAILABLE:
            pyautogui.hotkey("alt", "f4")
            return "Closed active window."
        return "Close active window unavailable."

    def lock_workstation(self) -> str:
        """Lock the computer workstation."""
        if sys.platform == "win32":
            try:
                ctypes.windll.user32.LockWorkStation()
                return "Computer workstation locked."
            except Exception as err:
                return f"Could not lock computer: {err}"
        return "Lock workstation is only supported on Windows."

    # =========================================================================
    # KEYBOARD, MOUSE & CLIPBOARD
    # =========================================================================

    def type_text(self, text: str, interval: float = 0.02) -> str:
        """Type text into focused application."""
        if not PYAUTOGUI_AVAILABLE:
            return "Typing automation requires pyautogui."
        try:
            pyautogui.write(text, interval=interval)
            return f"Typed '{text}' into active application."
        except Exception as err:
            return f"Error typing text: {err}"

    def press_shortcut(self, *keys: str) -> str:
        """Press a keyboard combination (e.g. 'ctrl', 's')."""
        if not PYAUTOGUI_AVAILABLE:
            return "Key shortcut requires pyautogui."
        try:
            pyautogui.hotkey(*keys)
            return f"Pressed shortcut: {' + '.join(keys)}"
        except Exception as err:
            return f"Error pressing shortcut: {err}"

    def press_key(self, key_name: str) -> str:
        """Press an individual keyboard key (enter, space, tab, esc)."""
        if not PYAUTOGUI_AVAILABLE:
            return "Key press requires pyautogui."
        try:
            pyautogui.press(key_name.lower())
            return f"Pressed key '{key_name}'."
        except Exception as err:
            return f"Error pressing key: {err}"

    def click_mouse(self, x: Optional[int] = None, y: Optional[int] = None) -> str:
        """Perform a mouse click at current or specified coordinates."""
        if not PYAUTOGUI_AVAILABLE:
            return "Mouse click requires pyautogui."
        try:
            if x is not None and y is not None:
                pyautogui.click(x, y)
                return f"Clicked mouse at ({x}, {y})."
            pyautogui.click()
            return "Clicked mouse at current position."
        except Exception as err:
            return f"Error clicking mouse: {err}"

    def get_clipboard(self) -> str:
        """Read system clipboard content."""
        if PYPERCLIP_AVAILABLE:
            try:
                content = pyperclip.paste()
                return content if content else "Clipboard is empty."
            except Exception as err:
                return f"Error reading clipboard: {err}"
        return "Clipboard tool unavailable."

    def set_clipboard(self, text: str) -> str:
        """Copy text to system clipboard."""
        if PYPERCLIP_AVAILABLE:
            try:
                pyperclip.copy(text)
                return f"Copied to clipboard."
            except Exception as err:
                return f"Error copying to clipboard: {err}"
        return "Clipboard tool unavailable."

    # =========================================================================
    # AUDIO & MEDIA
    # =========================================================================

    def control_volume(self, action: str) -> str:
        """Adjust system volume (up, down, mute)."""
        if not PYAUTOGUI_AVAILABLE:
            return "Volume control requires pyautogui."
        try:
            if action == "up":
                pyautogui.press("volumeup", presses=5)
                return "Turned volume up."
            elif action == "down":
                pyautogui.press("volumedown", presses=5)
                return "Turned volume down."
            elif action in ("mute", "unmute"):
                pyautogui.press("volumemute")
                return "Toggled volume mute."
            return "Unknown volume action."
        except Exception as err:
            return f"Error controlling volume: {err}"

    def control_media(self, action: str) -> str:
        """Control media playback (play/pause, next, previous)."""
        if not PYAUTOGUI_AVAILABLE:
            return "Media playback control requires pyautogui."
        try:
            if action in ("play", "pause", "playpause"):
                pyautogui.press("playpause")
                return "Toggled media playback."
            elif action in ("next", "nexttrack"):
                pyautogui.press("nexttrack")
                return "Skipped to next track."
            elif action in ("prev", "previous", "prevtrack"):
                pyautogui.press("prevtrack")
                return "Skipped to previous track."
            return "Unknown media action."
        except Exception as err:
            return f"Media control error: {err}"

    # =========================================================================
    # SYSTEM DIAGNOSTICS & TELEMETRY
    # =========================================================================

    def get_system_telemetry(self) -> dict[str, Any]:
        """Fetch real-time CPU, RAM, Disk, and Battery diagnostics."""
        telemetry: dict[str, Any] = {
            "os": f"{platform.system()} {platform.release()}",
            "arch": platform.machine(),
            "cpu_percent": 0.0,
            "ram_percent": 0.0,
            "ram_free_gb": 0.0,
            "disk_free_gb": 0.0,
            "battery_percent": None,
            "battery_charging": None,
        }
        if PSUTIL_AVAILABLE:
            try:
                telemetry["cpu_percent"] = psutil.cpu_percent(interval=0.1)
                mem = psutil.virtual_memory()
                telemetry["ram_percent"] = mem.percent
                telemetry["ram_free_gb"] = round(mem.available / (1024 ** 3), 1)

                root_drive = "C:" if sys.platform == "win32" else "/"
                disk = psutil.disk_usage(root_drive)
                telemetry["disk_free_gb"] = round(disk.free / (1024 ** 3), 1)

                bat = psutil.sensors_battery()
                if bat is not None:
                    telemetry["battery_percent"] = bat.percent
                    telemetry["battery_charging"] = bat.power_plugged
            except Exception:
                pass
        return telemetry

    def get_system_specs_text(self) -> str:
        """Format system diagnostics into a clean human-readable summary."""
        h = self.get_system_telemetry()
        specs = (
            f"OS: {h['os']} ({h['arch']})\n"
            f"CPU Load: {h['cpu_percent']}%\n"
            f"RAM Used: {h['ram_percent']}% ({h['ram_free_gb']} GB available)\n"
            f"Disk Free: {h['disk_free_gb']} GB"
        )
        if h["battery_percent"] is not None:
            status = "Charging" if h["battery_charging"] else "On battery"
            specs += f"\nBattery: {h['battery_percent']}% ({status})"
        return specs
