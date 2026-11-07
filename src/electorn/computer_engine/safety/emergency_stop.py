"""Global Emergency Stop for HACE Desktop Automation."""

from __future__ import annotations

import threading
import time
from typing import Callable, List, Optional


class EmergencyStop:
    """Thread-safe global emergency stop mechanism."""
    _instance: Optional[EmergencyStop] = None
    _lock = threading.Lock()

    def __new__(cls) -> EmergencyStop:
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._is_stopped = False
                cls._instance._reason = ""
                cls._instance._timestamp = 0.0
                cls._instance._listeners: List[Callable[[str], None]] = []
            return cls._instance

    @classmethod
    def get_instance(cls) -> EmergencyStop:
        return cls()

    def trigger(self, reason: str = "User initiated Emergency Stop") -> None:
        """Instantly abort all pending actions."""
        self._is_stopped = True
        self._reason = reason
        self._timestamp = time.time()
        for cb in list(self._listeners):
            try:
                cb(reason)
            except Exception:
                pass

    def reset(self) -> None:
        """Reset emergency stop state for new tasks."""
        self._is_stopped = False
        self._reason = ""
        self._timestamp = 0.0

    def check(self) -> bool:
        """Return True if emergency stop has been activated."""
        return self._is_stopped

    def get_reason(self) -> str:
        return self._reason

    def add_listener(self, cb: Callable[[str], None]) -> Callable[[], None]:
        self._listeners.append(cb)
        return lambda: self._listeners.remove(cb) if cb in self._listeners else None
