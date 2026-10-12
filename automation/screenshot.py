"""Screenshot and display capture automation for Electorn AI."""

from __future__ import annotations

import pathlib
import time
from typing import Any, Optional

try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
except Exception:
    PYAUTOGUI_AVAILABLE = False


class ScreenshotCapture:
    """Captures desktop screenshots and saves timestamped images."""

    def __init__(self, output_dir: Optional[str | pathlib.Path] = None) -> None:
        self.output_dir = pathlib.Path(output_dir or pathlib.Path.home() / "Desktop").resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def capture_fullscreen(self, filename: Optional[str] = None) -> dict[str, Any]:
        """Capture entire primary display."""
        if not PYAUTOGUI_AVAILABLE:
            return {"success": False, "message": "pyautogui is required for screen capture."}

        target_name = filename or f"screenshot_{int(time.time())}.png"
        target_path = self.output_dir / target_name
        try:
            img = pyautogui.screenshot()
            img.save(str(target_path))
            return {
                "success": True,
                "file_path": str(target_path),
                "dimensions": img.size,
                "message": f"Saved screenshot to '{target_path.name}'.",
            }
        except Exception as err:
            return {"success": False, "message": f"Failed to capture screenshot: {err}"}
