"""Background monitoring service for Windows with quiet-hours, rate-limiting, and error recovery."""

from __future__ import annotations

from datetime import datetime, timezone
import logging
import threading
import time
from typing import Optional

from electorn.assistant.supervisor import AssistantSupervisor

logger = logging.getLogger(__name__)


class AssistantMonitorService:
    """Windows background polling service for authorized Gmail and WhatsApp feeds."""

    def __init__(self, supervisor: Optional[AssistantSupervisor] = None, poll_interval_sec: int = 60) -> None:
        self.supervisor = supervisor or AssistantSupervisor()
        self.poll_interval = poll_interval_sec
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._is_running = False

    def is_quiet_hours(self) -> bool:
        """Check if current local time is within configured quiet hours."""
        cfg = self.supervisor.assistant_cfg
        if not cfg.quiet_hours_start or not cfg.quiet_hours_end:
            return False

        now_str = datetime.now().strftime("%H:%M")
        start, end = cfg.quiet_hours_start, cfg.quiet_hours_end

        if start <= end:
            return start <= now_str <= end
        else:
            # Over midnight (e.g. 22:00 to 07:00)
            return now_str >= start or now_str <= end

    def start(self) -> str:
        """Start background daemon thread safely."""
        if self._is_running:
            return "Monitor service is already running."

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        self._is_running = True
        return f"Personal Assistant background monitor started (polling every {self.poll_interval}s)."

    def stop(self) -> str:
        """Signal and stop background monitoring cleanly."""
        if not self._is_running:
            return "Monitor service is not running."

        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3.0)
        self._is_running = False
        return "Personal Assistant background monitor stopped cleanly."

    def _run_loop(self) -> None:
        """Main service polling loop."""
        while not self._stop_event.is_set():
            if not self.is_quiet_hours() and not self.supervisor.assistant_cfg.is_paused:
                try:
                    # Sync email if connected
                    if self.supervisor.email_connector.is_connected():
                        self.supervisor.sync_email(max_count=5)
                except Exception as e:
                    logger.warning(f"Background email sync error (will retry next interval): {e}")

            # Sleep poll_interval checking stop_event in 1-second chunks
            for _ in range(self.poll_interval):
                if self._stop_event.is_set():
                    break
                time.sleep(1.0)
