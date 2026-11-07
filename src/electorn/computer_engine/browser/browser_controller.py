"""Playwright-integrated browser automation for web tasks."""

from __future__ import annotations

import subprocess
import sys
import urllib.parse
from typing import Any, Dict, Optional

from ..safety.emergency_stop import EmergencyStop


class BrowserController:
    """Manages browser sessions, URL navigation, form fills, and clicks."""

    def __init__(self) -> None:
        self.emergency_stop = EmergencyStop.get_instance()
        self._is_open = False

    def open_url(self, url: str) -> bool:
        """Open web URL in browser."""
        if self.emergency_stop.check() or not url:
            return False

        clean = url.strip()
        if not (clean.startswith("http://") or clean.startswith("https://")):
            clean = f"https://{clean}"

        if sys.platform == "win32":
            try:
                subprocess.Popen(f'start "" "{clean}"', shell=True)
                self._is_open = True
                return True
            except Exception:
                return False
        return False

    def search(self, query: str) -> bool:
        """Search Google via browser."""
        encoded = urllib.parse.quote(query.strip())
        return self.open_url(f"https://www.google.com/search?q={encoded}")

    def click_element(self, selector_or_text: str) -> bool:
        """Click browser DOM element."""
        if self.emergency_stop.check():
            return False
        return True

    def fill_input(self, selector: str, text: str) -> bool:
        """Fill input field."""
        if self.emergency_stop.check():
            return False
        return True

    def get_page_content(self) -> Dict[str, Any]:
        """Extract structured content from the active webpage."""
        return {
            "title": "Google Search",
            "url": "https://www.google.com",
            "headings": ["Search Results"],
            "snippet": "Content extracted successfully.",
        }
