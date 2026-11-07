"""Native clipboard manager with context backup and restoration."""

from __future__ import annotations

import subprocess
import sys
from typing import List

try:
    import pyperclip
    PYPERCLIP_AVAILABLE = True
except Exception:
    PYPERCLIP_AVAILABLE = False


class ClipboardController:
    """Manages reading, writing, and restoring system clipboard text."""

    def __init__(self) -> None:
        self._history: List[str] = []

    def get_text(self) -> str:
        """Read current text from clipboard."""
        if PYPERCLIP_AVAILABLE:
            try:
                return pyperclip.paste()
            except Exception:
                pass

        if sys.platform == "win32":
            try:
                res = subprocess.run(
                    ["powershell", "-NoProfile", "-Command", "Get-Clipboard -Raw"],
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=2,
                )
                return res.stdout or ""
            except Exception:
                pass
        return ""

    def set_text(self, text: str) -> None:
        """Write text to clipboard with Unicode support."""
        if PYPERCLIP_AVAILABLE:
            try:
                pyperclip.copy(text)
                return
            except Exception:
                pass

        if sys.platform == "win32":
            try:
                p = subprocess.Popen(["powershell", "-NoProfile", "-Command", "Set-Clipboard"], stdin=subprocess.PIPE, text=True, encoding="utf-8")
                p.communicate(input=text, timeout=2)
            except Exception:
                pass

    def clear(self) -> None:
        """Clear clipboard contents."""
        self.set_text("")

    def backup(self) -> None:
        """Save current clipboard text onto stack."""
        self._history.append(self.get_text())

    def restore(self) -> None:
        """Pop and restore previous clipboard content."""
        if self._history:
            prev = self._history.pop()
            self.set_text(prev)
