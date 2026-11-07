"""
Browser navigation stack and history manager.
"""

from typing import List, Optional
from electorn.computer_engine.safety.emergency_stop import EmergencyStop


class BrowserNavigator:
    def __init__(self) -> None:
        self._emergency_stop = EmergencyStop.get_instance()
        self._history_stack: List[str] = []
        self._forward_stack: List[str] = []

    def navigate(self, url: str) -> bool:
        if self._emergency_stop.check():
            return False
        self._history_stack.append(url)
        self._forward_stack.clear()
        return True

    def back(self) -> bool:
        if len(self._history_stack) <= 1:
            return False
        current = self._history_stack.pop()
        self._forward_stack.append(current)
        return True

    def forward(self) -> bool:
        if not self._forward_stack:
            return False
        next_url = self._forward_stack.pop()
        self._history_stack.append(next_url)
        return True

    def reload(self) -> bool:
        return not self._emergency_stop.check()
