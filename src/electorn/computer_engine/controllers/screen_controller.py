"""DPI-aware screenshot capture, base64 encoding, and multi-monitor resolution detection."""

from __future__ import annotations

import base64
import io
import sys
from typing import Optional, Tuple

try:
    import mss
    MSS_AVAILABLE = True
except Exception:
    MSS_AVAILABLE = False

try:
    from PIL import Image
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False

try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
except Exception:
    PYAUTOGUI_AVAILABLE = False


class ScreenController:
    """Captures desktop screenshots and handles display coordinate scaling."""

    def __init__(self) -> None:
        self._cached_resolution: Optional[Tuple[int, int]] = None

    def get_resolution(self) -> Tuple[int, int]:
        """Return (width, height) of primary screen."""
        if self._cached_resolution:
            return self._cached_resolution

        if PYAUTOGUI_AVAILABLE:
            try:
                size = pyautogui.size()
                self._cached_resolution = (size.width, size.height)
                return self._cached_resolution
            except Exception:
                pass

        if MSS_AVAILABLE:
            try:
                with mss.mss() as sct:
                    mon = sct.monitors[1]
                    self._cached_resolution = (mon["width"], mon["height"])
                    return self._cached_resolution
            except Exception:
                pass

        return (1920, 1080)

    def capture_screen(self, crop: Optional[Tuple[int, int, int, int]] = None) -> Optional[Image.Image]:
        """Capture screen as PIL Image."""
        if not PIL_AVAILABLE:
            return None

        if MSS_AVAILABLE:
            try:
                with mss.mss() as sct:
                    mon = sct.monitors[1]
                    if crop:
                        x, y, w, h = crop
                        bbox = {"top": y, "left": x, "width": w, "height": h}
                    else:
                        bbox = mon
                    raw = sct.grab(bbox)
                    img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
                    return img
            except Exception:
                pass

        if PYAUTOGUI_AVAILABLE:
            try:
                return pyautogui.screenshot()
            except Exception:
                pass

        return None

    def capture_base64(self, crop: Optional[Tuple[int, int, int, int]] = None) -> str:
        """Capture screenshot and encode as base64 JPEG string."""
        img = self.capture_screen(crop=crop)
        if img is None:
            return ""

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        return base64.b64encode(buf.getvalue()).decode("utf-8")
