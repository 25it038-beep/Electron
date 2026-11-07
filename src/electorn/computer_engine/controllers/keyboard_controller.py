"""Speed-controlled, natural keyboard automation with multilingual Unicode support."""

from __future__ import annotations

import time
from typing import List, Optional

from ..safety.emergency_stop import EmergencyStop
from .clipboard_controller import ClipboardController

try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
except Exception:
    PYAUTOGUI_AVAILABLE = False


class KeyboardController:
    """Controls keystroke simulation, natural text typing, and key combinations."""

    def __init__(self, clipboard: Optional[ClipboardController] = None) -> None:
        self.clipboard = clipboard or ClipboardController()
        self.emergency_stop = EmergencyStop.get_instance()
        self.wpm = 80
        self.char_delay = 0.02

    def set_typing_speed(self, words_per_minute: int) -> None:
        """Configure typing speed (Words Per Minute)."""
        self.wpm = max(10, words_per_minute)
        self.char_delay = 12.0 / self.wpm

    def type_text(self, text: str, wpm: Optional[int] = None, use_clipboard: bool = True) -> bool:
        """Type text into focused element with natural pacing and multilingual support."""
        if self.emergency_stop.check() or not text:
            return False

        delay = (12.0 / wpm) if wpm else self.char_delay
        has_unicode = any(ord(c) > 127 for c in text)

        # For non-ASCII unicode (Tamil, emojis, special symbols) or long text, use instantaneous clipboard paste
        if (has_unicode or len(text) > 60) and use_clipboard:
            return self.paste_text(text)

        if PYAUTOGUI_AVAILABLE:
            try:
                pyautogui.write(text, interval=delay)
            except Exception:
                return self.paste_text(text)
        return not self.emergency_stop.check()

    def paste_text(self, text: str) -> bool:
        """Paste text safely via system clipboard."""
        if self.emergency_stop.check() or not text:
            return False
        self.clipboard.set_text(text)
        time.sleep(0.04)
        ok = self.press_shortcut("ctrl", "v")
        time.sleep(0.04)
        return ok

    def press_key(self, key_name: str) -> bool:
        """Press single key (e.g. 'enter', 'esc', 'tab', 'backspace')."""
        if self.emergency_stop.check():
            return False
        clean = key_name.strip().lower()
        key_map = {
            "enter": "enter",
            "return": "enter",
            "esc": "esc",
            "escape": "esc",
            "tab": "tab",
            "space": "space",
            "backspace": "backspace",
            "del": "delete",
            "delete": "delete",
            "up": "up",
            "down": "down",
            "left": "left",
            "right": "right",
        }
        target = key_map.get(clean, clean)
        if PYAUTOGUI_AVAILABLE:
            try:
                pyautogui.press(target)
            except Exception:
                pass
        return not self.emergency_stop.check()

    def press_shortcut(self, *keys: str) -> bool:
        """Press keyboard shortcut combination (e.g. 'ctrl', 's')."""
        if self.emergency_stop.check() or not keys:
            return False
        clean_keys = [k.strip().lower() for k in keys]
        if PYAUTOGUI_AVAILABLE:
            try:
                pyautogui.hotkey(*clean_keys)
            except Exception:
                pass
        return not self.emergency_stop.check()

    def hotkey(self, *keys: str) -> bool:
        """Alias for press_shortcut."""
        return self.press_shortcut(*keys)

    def select_all(self) -> bool:
        return self.press_shortcut("ctrl", "a")

    def copy(self) -> bool:
        return self.press_shortcut("ctrl", "c")

    def paste(self) -> bool:
        return self.press_shortcut("ctrl", "v")

    def undo(self) -> bool:
        return self.press_shortcut("ctrl", "z")

    def redo(self) -> bool:
        return self.press_shortcut("ctrl", "y")
