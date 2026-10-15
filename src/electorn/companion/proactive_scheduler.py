"""Event-driven proactive communication scheduler with anti-annoyance filters."""

from __future__ import annotations

from datetime import datetime, time as dtime
import time
from typing import List, Optional
import uuid

from electorn.companion.schema import (
    CompanionConfig,
    CompanionMode,
    CompanionState,
    ConversationFrequency,
    ProactiveEvent,
    ScreenObservationReport,
)


class ProactiveScheduler:
    """Evaluates when the companion should speak proactively without irritating the user."""

    def __init__(self, config: CompanionConfig, state: CompanionState) -> None:
        self.config = config
        self.state = state
        self._last_error_spoken: Optional[str] = None
        self._last_break_reminder_time: float = 0.0

    def is_in_quiet_hours(self) -> bool:
        """Check if current time falls within configured quiet hours."""
        if not self.config.personality.quiet_hours_enabled:
            return False

        try:
            now_time = datetime.now().time()
            start_parts = [int(p) for p in self.config.personality.quiet_hours_start.split(":")]
            end_parts = [int(p) for p in self.config.personality.quiet_hours_end.split(":")]
            start = dtime(start_parts[0], start_parts[1])
            end = dtime(end_parts[0], end_parts[1])

            if start <= end:
                return start <= now_time <= end
            else:
                # Spans midnight (e.g. 22:30 to 08:00)
                return now_time >= start or now_time <= end
        except Exception:
            return False

    def can_speak_proactively(self, priority: str = "medium") -> bool:
        """Verify whether an unsolicited proactive remark is permitted right now."""
        # 1. Mode check
        if self.state.active_mode in (CompanionMode.PASSIVE, CompanionMode.PRIVACY):
            return False

        # 2. Pause check
        if self.state.is_paused:
            return False

        # 3. Focus mode check: only urgent alerts pass through
        if self.state.active_mode == CompanionMode.FOCUS and priority not in ("urgent", "high"):
            return False

        # 4. Daily limit check
        if self.state.proactive_messages_today >= self.config.personality.proactive_daily_limit:
            return False

        # 5. Quiet hours check
        if self.is_in_quiet_hours() and priority != "urgent":
            return False

        # 6. Cooldown interval check
        now = time.time()
        last_speech = self.state.last_companion_speech_time or 0.0
        interval = now - last_speech

        min_interval = self.config.personality.min_interval_seconds
        # Dynamic frequency scale
        if self.config.personality.conversation_frequency == ConversationFrequency.LOW:
            min_interval = max(min_interval, 1800)  # 30 min minimum
        elif self.config.personality.conversation_frequency == ConversationFrequency.HIGH:
            min_interval = min(min_interval, 300)   # 5 min minimum

        # Urgent events bypass cooldown
        if priority == "urgent":
            return True

        # High priority events (code errors) allow shorter cooldown
        if priority == "high" and interval >= 60:
            return True

        return interval >= min_interval

    def check_observation_event(self, report: ScreenObservationReport) -> Optional[ProactiveEvent]:
        """Check if a fresh screen observation report warrants a proactive response."""
        if not report or report.is_excluded:
            return None

        # Detect new code errors or exceptions
        if report.visible_error and report.visible_error != self._last_error_spoken:
            if self.can_speak_proactively(priority="high"):
                self._last_error_spoken = report.visible_error
                return ProactiveEvent(
                    event_id=f"evt-{uuid.uuid4().hex[:8]}",
                    event_type="error_detected",
                    priority="high",
                    title=report.visible_error,
                    details=f"Error in {report.window_title}",
                    suggested_speech=f"Darling, I noticed this error in your editor: '{report.visible_error}'. Want me to take a look?",
                )

        return None

    def check_time_based_events(self) -> Optional[ProactiveEvent]:
        """Check for session milestone break reminders or idle check-ins."""
        now = time.time()

        # 1. Break reminder after 50 continuous minutes of work
        work_duration = now - self.state.session_start_time
        if work_duration >= 3000 and (now - self._last_break_reminder_time) >= 3000:
            if self.can_speak_proactively(priority="medium"):
                self._last_break_reminder_time = now
                return ProactiveEvent(
                    event_id=f"evt-{uuid.uuid4().hex[:8]}",
                    event_type="long_work_session",
                    priority="medium",
                    title="Time for a stretch and hydration break",
                    details=f"Continuous session for {int(work_duration / 60)} minutes",
                )

        # 2. Idle check-in in Companion mode (quiet for 35 min)
        last_activity = max(
            self.state.last_user_speech_time or self.state.session_start_time,
            self.state.last_companion_speech_time or self.state.session_start_time,
        )
        if (now - last_activity) >= 2100 and self.state.active_mode == CompanionMode.COMPANION:
            if self.can_speak_proactively(priority="low"):
                return ProactiveEvent(
                    event_id=f"evt-{uuid.uuid4().hex[:8]}",
                    event_type="check_in",
                    priority="low",
                    title="Gentle check-in",
                    details="User idle/quiet in companion mode",
                )

        return None

    def record_speech_delivered(self) -> None:
        """Mark that a proactive remark was voiced, updating timestamps and counts."""
        self.state.last_companion_speech_time = time.time()
        self.state.proactive_messages_today += 1
