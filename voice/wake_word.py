"""Wake-word detection module for Electorn AI."""

from __future__ import annotations

import re


class WakeWordDetector:
    """Detects activation phrases (e.g. 'Hey Electorn', 'Electorn') in speech."""

    def __init__(self, wake_words: Optional[list[str]] = None) -> None:
        self.wake_words = wake_words or ["hey electorn", "electorn", "electron", "ok electorn"]

    def contains_wake_word(self, transcript: str) -> bool:
        """Check if transcript contains one of the configured wake words."""
        lower = transcript.strip().lower()
        return any(ww in lower for ww in self.wake_words)

    def extract_command(self, transcript: str) -> str:
        """Strip the wake word prefix from the command."""
        lower = transcript.strip().lower()
        for ww in self.wake_words:
            if lower.startswith(ww):
                return transcript[len(ww):].strip(" ,:.-")
        return transcript.strip()
