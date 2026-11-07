"""Low-latency, human-like mouse automation with cubic Bézier trajectory smoothing."""

from __future__ import annotations

import math
import random
import sys
import time
from typing import Optional, Tuple

from ..safety.emergency_stop import EmergencyStop

try:
    import pyautogui
    pyautogui.FAILSAFE = True
    PYAUTOGUI_AVAILABLE = True
except Exception:
    PYAUTOGUI_AVAILABLE = False


class MouseController:
    """Controls mouse movement, natural clicks, drag and drop, and scrolling."""

    def __init__(self) -> None:
        self.emergency_stop = EmergencyStop.get_instance()
        self._current_x = 0
        self._current_y = 0
        self._refresh_position()

    def _refresh_position(self) -> Tuple[int, int]:
        if PYAUTOGUI_AVAILABLE:
            try:
                pos = pyautogui.position()
                self._current_x, self._current_y = pos.x, pos.y
                return (self._current_x, self._current_y)
            except Exception:
                pass
        return (self._current_x, self._current_y)

    def get_position(self) -> Tuple[int, int]:
        """Return current cursor position."""
        return self._refresh_position()

    def set_position(self, x: int, y: int) -> bool:
        """Instantly teleport cursor to (x, y)."""
        if self.emergency_stop.check():
            return False
        self._current_x, self._current_y = int(x), int(y)
        if PYAUTOGUI_AVAILABLE:
            try:
                pyautogui.moveTo(self._current_x, self._current_y)
            except Exception:
                pass
        return not self.emergency_stop.check()

    def smooth_move(self, target_x: int, target_y: int, duration_s: float = 0.25) -> bool:
        """Move cursor naturally using cubic Bézier curve easing."""
        if self.emergency_stop.check():
            return False

        start_x, start_y = self._refresh_position()
        end_x, end_y = int(target_x), int(target_y)

        if start_x == end_x and start_y == end_y:
            return True

        delta_x = end_x - start_x
        delta_y = end_y - start_y

        # Generate random natural control points
        ctrl1_x = start_x + delta_x * random.uniform(0.15, 0.35)
        ctrl1_y = start_y + delta_y * random.uniform(0.05, 0.25)
        ctrl2_x = start_x + delta_x * random.uniform(0.60, 0.85)
        ctrl2_y = start_y + delta_y * random.uniform(0.65, 0.90)

        steps = max(10, int(duration_s * 60))
        step_sleep = duration_s / steps

        for i in range(1, steps + 1):
            if self.emergency_stop.check():
                return False

            t = i / steps
            x = int(
                (1 - t) ** 3 * start_x
                + 3 * (1 - t) ** 2 * t * ctrl1_x
                + 3 * (1 - t) * t ** 2 * ctrl2_x
                + t ** 3 * end_x
            )
            y = int(
                (1 - t) ** 3 * start_y
                + 3 * (1 - t) ** 2 * t * ctrl1_y
                + 3 * (1 - t) * t ** 2 * ctrl2_y
                + t ** 3 * end_y
            )

            if PYAUTOGUI_AVAILABLE:
                try:
                    pyautogui.moveTo(x, y)
                except Exception:
                    pass
            self._current_x, self._current_y = x, y
            time.sleep(step_sleep)

        self.set_position(end_x, end_y)
        return not self.emergency_stop.check()

    def move_to(self, target_x: int, target_y: int, duration_s: float = 0.25) -> bool:
        """Alias for smooth_move."""
        return self.smooth_move(target_x, target_y, duration_s)

    def click(self, x: Optional[int] = None, y: Optional[int] = None) -> bool:
        """Perform left-click at target coordinates or current position."""
        if self.emergency_stop.check():
            return False
        if x is not None and y is not None:
            self.smooth_move(x, y)

        if PYAUTOGUI_AVAILABLE:
            try:
                pyautogui.click()
            except Exception:
                pass
        return not self.emergency_stop.check()

    def right_click(self, x: Optional[int] = None, y: Optional[int] = None) -> bool:
        """Perform right-click at target coordinates or current position."""
        if self.emergency_stop.check():
            return False
        if x is not None and y is not None:
            self.smooth_move(x, y)

        if PYAUTOGUI_AVAILABLE:
            try:
                pyautogui.rightClick()
            except Exception:
                pass
        return not self.emergency_stop.check()

    def double_click(self, x: Optional[int] = None, y: Optional[int] = None) -> bool:
        """Perform double-click."""
        if self.emergency_stop.check():
            return False
        if x is not None and y is not None:
            self.smooth_move(x, y)

        if PYAUTOGUI_AVAILABLE:
            try:
                pyautogui.doubleClick()
            except Exception:
                pass
        return not self.emergency_stop.check()

    def mouse_down(self, x: Optional[int] = None, y: Optional[int] = None) -> bool:
        """Press and hold mouse button."""
        if self.emergency_stop.check():
            return False
        if x is not None and y is not None:
            self.smooth_move(x, y)
        if PYAUTOGUI_AVAILABLE:
            try:
                pyautogui.mouseDown()
            except Exception:
                pass
        return not self.emergency_stop.check()

    def mouse_up(self, x: Optional[int] = None, y: Optional[int] = None) -> bool:
        """Release mouse button."""
        if self.emergency_stop.check():
            return False
        if x is not None and y is not None:
            self.smooth_move(x, y)
        if PYAUTOGUI_AVAILABLE:
            try:
                pyautogui.mouseUp()
            except Exception:
                pass
        return not self.emergency_stop.check()

    def drag_and_drop(self, from_x: int, from_y: int, to_x: int, to_y: int, duration_s: float = 0.5) -> bool:
        """Drag from origin to destination."""
        if self.emergency_stop.check():
            return False
        self.smooth_move(from_x, from_y)
        self.mouse_down()
        time.sleep(0.08)
        self.smooth_move(to_x, to_y, duration_s=duration_s)
        time.sleep(0.08)
        self.mouse_up()
        return not self.emergency_stop.check()

    def hover(self, x: int, y: int, duration_s: float = 0.3) -> bool:
        """Hover cursor over target coordinates."""
        if self.emergency_stop.check():
            return False
        self.smooth_move(x, y)
        time.sleep(duration_s)
        return not self.emergency_stop.check()

    def scroll(self, delta_y: int = 5, delta_x: int = 0) -> bool:
        """Scroll vertically and horizontally."""
        if self.emergency_stop.check():
            return False
        if PYAUTOGUI_AVAILABLE:
            try:
                pyautogui.scroll(int(delta_y * 100))
                if delta_x != 0 and hasattr(pyautogui, "hscroll"):
                    pyautogui.hscroll(int(delta_x * 100))
            except Exception:
                pass
        return not self.emergency_stop.check()
