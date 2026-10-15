"""Windows startup service management and single-instance process guard."""

from __future__ import annotations

import logging
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Optional, Tuple

if sys.platform == "win32":
    try:
        import winreg
        WINREG_AVAILABLE = True
    except ImportError:
        WINREG_AVAILABLE = False
else:
    WINREG_AVAILABLE = False

logger = logging.getLogger(__name__)

REG_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "ElectornCompanion"


class StartupManager:
    """Manages Windows automatic login startup without requiring administrative elevation."""

    def __init__(self, lock_dir: Optional[Path] = None) -> None:
        self.lock_dir = lock_dir or (Path.home() / ".electorn" / "companion")
        self.lock_file = self.lock_dir / "companion.lock"
        self._lock_acquired = False

    def is_startup_enabled(self) -> bool:
        """Check if Electorn Companion is registered in Windows startup registry."""
        if not WINREG_AVAILABLE or sys.platform != "win32":
            return False

        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_RUN_KEY, 0, winreg.KEY_READ)
            try:
                val, _ = winreg.QueryValueEx(key, APP_NAME)
                return bool(val)
            except FileNotFoundError:
                return False
            finally:
                winreg.CloseKey(key)
        except Exception as e:
            logger.debug("Failed to inspect startup registry: %s", e)
            return False

    def enable_startup(self) -> Tuple[bool, str]:
        """Register Electorn Companion to start automatically on Windows user login."""
        if sys.platform != "win32" or not WINREG_AVAILABLE:
            return False, "Automatic login startup is only supported on Windows."

        try:
            # Build execution command using current python interpreter and module
            python_exe = sys.executable
            # e.g.: "C:\Python314\pythonw.exe" -m electorn companion start
            cmd = f'"{python_exe}" -m electorn companion start'

            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_RUN_KEY, 0, winreg.KEY_SET_VALUE)
            try:
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd)
                return True, "Successfully registered Electorn Companion in Windows startup (HKCU Run)."
            finally:
                winreg.CloseKey(key)
        except Exception as e:
            return False, f"Failed to enable startup: {e}"

    def disable_startup(self) -> Tuple[bool, str]:
        """Remove Electorn Companion from Windows user login startup."""
        if sys.platform != "win32" or not WINREG_AVAILABLE:
            return False, "Automatic login startup is only supported on Windows."

        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_RUN_KEY, 0, winreg.KEY_SET_VALUE)
            try:
                winreg.DeleteValue(key, APP_NAME)
                return True, "Successfully disabled Electorn Companion Windows startup."
            except FileNotFoundError:
                return True, "Electorn Companion was not registered in startup."
            finally:
                winreg.CloseKey(key)
        except Exception as e:
            return False, f"Failed to disable startup: {e}"

    # =========================================================================
    # SINGLE INSTANCE PROCESS GUARD
    # =========================================================================

    def acquire_instance_lock(self) -> bool:
        """Prevent duplicate background instances from running simultaneously."""
        self.lock_dir.mkdir(parents=True, exist_ok=True)

        if self.lock_file.exists():
            try:
                pid_str = self.lock_file.read_text().strip()
                if pid_str.isdigit():
                    existing_pid = int(pid_str)
                    # Check if process is still running
                    if sys.platform == "win32":
                        import psutil
                        if psutil.pid_exists(existing_pid):
                            return False # Another instance is active
            except Exception:
                pass

        try:
            self.lock_file.write_text(str(os.getpid()))
            self._lock_acquired = True
            return True
        except Exception:
            return False

    def release_instance_lock(self) -> None:
        """Release the instance lock upon clean exit."""
        if self._lock_acquired and self.lock_file.exists():
            try:
                self.lock_file.unlink()
            except Exception:
                pass
            self._lock_acquired = False
