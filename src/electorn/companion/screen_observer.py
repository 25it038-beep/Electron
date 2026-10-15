"""Screen observation engine with privacy filtering and visual change detection."""

from __future__ import annotations

import io
import logging
from pathlib import Path
import sys
import time
from typing import List, Optional, Tuple

try:
    from PIL import Image, ImageGrab, ImageOps
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

if sys.platform == "win32":
    try:
        import win32gui
        import win32process
        WIN32_AVAILABLE = True
    except ImportError:
        WIN32_AVAILABLE = False
else:
    WIN32_AVAILABLE = False

from electorn.companion.schema import ScreenObservationConfig, ScreenObservationReport

logger = logging.getLogger(__name__)


class ScreenObservationEngine:
    """Observes the user's workspace screen safely with privacy boundaries and change detection."""

    def __init__(self, config: Optional[ScreenObservationConfig] = None) -> None:
        self.config = config or ScreenObservationConfig()
        self._last_thumbnail: Optional[Any] = None
        self._last_capture_time: float = 0.0

    def get_active_window_info(self) -> Tuple[str, str]:
        """Retrieve the title and process name of the current foreground window."""
        window_title = "Unknown Window"
        process_name = "unknown"

        if sys.platform == "win32" and WIN32_AVAILABLE:
            try:
                hwnd = win32gui.GetForegroundWindow()
                if hwnd:
                    text = win32gui.GetWindowText(hwnd)
                    if text:
                        window_title = text.strip()

                    if PSUTIL_AVAILABLE:
                        _, pid = win32process.GetWindowThreadProcessId(hwnd)
                        if pid:
                            try:
                                proc = psutil.Process(pid)
                                process_name = proc.name().lower()
                            except Exception:
                                pass
            except Exception as e:
                logger.debug("Failed to get foreground window via win32: %s", e)

        return window_title, process_name

    def is_sensitive(self, window_title: str, process_name: str) -> bool:
        """Check whether the active window matches excluded private/security keywords."""
        target_str = f"{window_title.lower()} {process_name.lower()}"
        for keyword in self.config.excluded_apps:
            if keyword.strip().lower() in target_str:
                return True
        return False

    def categorize_window(self, window_title: str, process_name: str) -> str:
        """Infer high-level application category (code_editor, terminal, browser, document, communication, other)."""
        combined = f"{window_title.lower()} {process_name.lower()}"

        if any(w in combined for w in ["code", "visual studio", "pycharm", "sublime", "vim", "nvim", "atom", "intellij", "cursor", "antigravity"]):
            return "code_editor"
        if any(w in combined for w in ["powershell", "cmd.exe", "terminal", "bash", "zsh", "alacritty", "iterm", "wezterm"]):
            return "terminal"
        if any(w in combined for w in ["chrome", "firefox", "msedge", "edge", "safari", "brave", "opera", "arc"]):
            return "browser"
        if any(w in combined for w in ["word", "excel", "powerpoint", "notepad", "obsidian", "notion", "pdf", "acrobat"]):
            return "document"
        if any(w in combined for w in ["slack", "teams", "discord", "whatsapp", "telegram", "outlook"]):
            return "communication"

        return "other"

    def compute_change_ratio(self, current_img: Any) -> float:
        """Calculate pixel variance between current capture and previous thumbnail."""
        if not PIL_AVAILABLE or current_img is None:
            return 1.0

        try:
            # Downsample to 32x32 grayscale
            thumb = current_img.resize((32, 32)).convert("L")
            if self._last_thumbnail is None:
                self._last_thumbnail = thumb
                return 1.0

            # Compare pixel difference
            diff = 0
            cur_pixels = list(thumb.getdata())
            prev_pixels = list(self._last_thumbnail.getdata())
            for c, p in zip(cur_pixels, prev_pixels):
                diff += abs(c - p)

            total_possible = 32 * 32 * 255
            ratio = float(diff) / float(total_possible)
            self._last_thumbnail = thumb
            return ratio
        except Exception as e:
            logger.debug("Error calculating visual change ratio: %s", e)
            return 1.0

    def capture_screen(self) -> Tuple[Optional[Any], ScreenObservationReport]:
        """Safely captures screen image and constructs observation metadata."""
        window_title, process_name = self.get_active_window_info()
        category = self.categorize_window(window_title, process_name)
        is_priv = self.is_sensitive(window_title, process_name)

        # Base report
        report = ScreenObservationReport(
            timestamp=time.time(),
            window_title=window_title,
            process_name=process_name,
            app_category=category,
            is_excluded=is_priv,
            change_ratio=0.0,
        )

        # Respect privacy boundary
        if not self.config.enabled:
            report.visible_summary = "Screen observation is disabled."
            return None, report

        if is_priv:
            report.visible_summary = f"Sensitive window detected ({process_name}). Screen capture suppressed."
            return None, report

        if not PIL_AVAILABLE:
            report.visible_summary = "PIL ImageGrab is not available in environment."
            return None, report

        # Capture active window or full screen
        captured_image = None
        try:
            if sys.platform == "win32" and WIN32_AVAILABLE and self.config.capture_active_window_only:
                hwnd = win32gui.GetForegroundWindow()
                if hwnd and win32gui.IsWindowVisible(hwnd):
                    rect = win32gui.GetWindowRect(hwnd)
                    # (left, top, right, bottom)
                    width = rect[2] - rect[0]
                    height = rect[3] - rect[1]
                    if width > 10 and height > 10:
                        captured_image = ImageGrab.grab(bbox=rect)

            if captured_image is None:
                # Full desktop fallback
                captured_image = ImageGrab.grab()

            self._last_capture_time = time.time()
            report.change_ratio = self.compute_change_ratio(captured_image)
        except Exception as e:
            logger.debug("Screen capture exception: %s", e)
            report.visible_summary = f"Screen capture error: {e}"
            return None, report

        return captured_image, report
