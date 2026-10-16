"""Event-driven proactive communication scheduler with anti-annoyance filters and bedtime awareness."""

from __future__ import annotations

from datetime import datetime, time as dtime
import time
from typing import List, Optional
import uuid

from electorn.companion.schema import (
    ActivityCategory,
    CompanionConfig,
    CompanionMode,
    CompanionState,
    ConversationFrequency,
    ProactiveEvent,
    ScreenObservationReport,
)
from electorn.companion.time_engine import TimeAwarenessEngine


class ProactiveScheduler:
    """Evaluates when the companion should speak proactively without irritating Harshan."""

    def __init__(self, config: CompanionConfig, state: CompanionState) -> None:
        self.config = config
        self.state = state
        self.time_engine = TimeAwarenessEngine()
        self._last_error_spoken: Optional[str] = None
        self._last_break_reminder_time: float = 0.0
        self._last_bedtime_stage_spoken: Optional[str] = None
        self._last_distraction_spoken_time: float = 0.0
        self._last_user_return_spoken_time: float = 0.0
        self._last_app_switch_spoken_time: float = 0.0
        self._last_idle_spoken_time: float = 0.0

    def is_in_quiet_hours(self) -> bool:
        """Check if current system time falls within configured quiet hours."""
        return self.time_engine.is_in_quiet_hours(self.config.bedtime)

    def can_speak_proactively(self, priority: int = 4) -> bool:
        """Verify whether an unsolicited proactive remark is permitted right now.
        
        Priority scale:
            1: Critical Security / System Notification
            2: User-Requested Reminder
            3: Important Deadline / Bedtime Stage
            4: Startup Greeting
            5: Contextual Assistance / Error / Distraction Check
            6: Casual Conversation
        """
        # 1. Proactive master toggle
        if not self.config.proactive.enabled:
            return False

        # 2. Mode checks
        if self.state.active_mode in (CompanionMode.PASSIVE, CompanionMode.PRIVACY):
            return False

        # 3. Pause / Mute check
        if self.state.is_paused or self.state.is_muted:
            return False

        # 4. Focus mode check: only priority 1 or 2 can interrupt
        if self.state.active_mode == CompanionMode.FOCUS and priority > 2:
            return False

        # 5. Night mode check: only bedtime or priority <= 3
        if self.state.active_mode == CompanionMode.NIGHT and priority > 3:
            return False

        # 6. Daily limit check
        if self.state.proactive_messages_today >= self.config.proactive.daily_limit:
            return False

        # 7. Hourly rate limit check
        now = time.time()
        current_hour = datetime.now().hour
        if self.state.current_hour_window != current_hour:
            self.state.current_hour_window = current_hour
            self.state.hourly_proactive_count = 0

        if self.state.hourly_proactive_count >= self.config.proactive.max_per_hour and priority > 2:
            return False

        # 8. Quiet hours check (permits security, user reminders, and bedtime reminders)
        if self.is_in_quiet_hours() and priority > 3:
            # If user is in an active interactive session or active COMPANION mode, allow conversational companion speech
            if self.config.proactive.allow_active_quiet_hours_override and (
                self.state.interactive_session_active or self.state.active_mode == CompanionMode.COMPANION
            ):
                pass
            else:
                return False

        # 9. Cooldown interval check
        last_speech = self.state.last_companion_speech_time or 0.0
        interval = now - last_speech

        min_interval = self.config.proactive.min_interval_seconds
        if self.config.personality.conversation_frequency == ConversationFrequency.LOW:
            min_interval = max(min_interval, 180)  # 3 min minimum
        elif self.config.personality.conversation_frequency == ConversationFrequency.HIGH:
            min_interval = min(min_interval, 45)   # 45 sec minimum

        # Priority 1 and 2 bypass cooldown
        if priority <= 2:
            return True

        # Priority 3 (bedtime / deadlines) allow 60s cooldown
        if priority == 3 and interval >= 60:
            return True

        return interval >= min_interval

    def check_startup_greeting(self) -> Optional[ProactiveEvent]:
        """Generate startup greeting event if not recently greeted in this login session."""
        now = time.time()
        last_startup = self.config.startup.last_startup_greeting_timestamp or 0.0

        # At least 30 minutes since last startup greeting
        if (now - last_startup) >= 1800:
            if self.can_speak_proactively(priority=4):
                self.config.startup.last_startup_greeting_timestamp = now
                return ProactiveEvent(
                    event_id=f"evt-{uuid.uuid4().hex[:8]}",
                    event_type="startup",
                    priority=4,
                    title="Startup Welcome",
                    details="Windows session startup",
                )
        return None

    def check_bedtime_event(self) -> Optional[ProactiveEvent]:
        """Check system clock for multi-stage bedtime reminders."""
        stage = self.time_engine.evaluate_bedtime_stage(self.config.bedtime)
        if not stage:
            return None

        # Check late night reminder limit
        if self.state.late_night_reminders_count >= self.config.bedtime.max_late_night_reminders:
            return None

        if stage != self._last_bedtime_stage_spoken and self.can_speak_proactively(priority=3):
            self._last_bedtime_stage_spoken = stage
            self.state.late_night_reminders_count += 1
            now_str = self.time_engine.get_formatted_time()
            bedtime_str = self.config.bedtime.bedtime

            return ProactiveEvent(
                event_id=f"evt-{uuid.uuid4().hex[:8]}",
                event_type=stage,
                priority=3,
                title=now_str,
                details=bedtime_str,
            )

        return None

    def check_distraction_event(self, report: ScreenObservationReport) -> Optional[ProactiveEvent]:
        """Check if user has been in an entertainment/video distraction for sustained duration."""
        if not report or report.is_excluded:
            return None

        now = time.time()
        # If sustained duration in entertainment or videos exceeds threshold (e.g. 40 min = 2400s)
        if report.activity_category in (ActivityCategory.WATCHING_VIDEOS, ActivityCategory.ENTERTAINMENT, ActivityCategory.GAMING):
            thresh = self.config.activity.distraction_threshold_seconds
            if report.sustained_duration_seconds >= thresh:
                if (now - self._last_distraction_spoken_time) >= thresh and self.can_speak_proactively(priority=5):
                    self._last_distraction_spoken_time = now
                    act_name = "watching videos" if report.activity_category == ActivityCategory.WATCHING_VIDEOS else "playing a game" if report.activity_category == ActivityCategory.GAMING else "on entertainment"
                    dur_min = int(report.sustained_duration_seconds / 60)
                    return ProactiveEvent(
                        event_id=f"evt-{uuid.uuid4().hex[:8]}",
                        event_type="distraction_check",
                        priority=5,
                        title=f"{act_name} for about {dur_min} minutes",
                        details=report.window_title,
                    )

        return None

    def check_observation_event(self, report: ScreenObservationReport) -> Optional[ProactiveEvent]:
        """Check if a fresh screen observation report warrants a proactive error alert."""
        if not report or report.is_excluded:
            return None

        # Detect new code errors or exceptions
        if report.visible_error and report.visible_error != self._last_error_spoken:
            if self.can_speak_proactively(priority=5):
                self._last_error_spoken = report.visible_error
                return ProactiveEvent(
                    event_id=f"evt-{uuid.uuid4().hex[:8]}",
                    event_type="error_detected",
                    priority=5,
                    title=report.visible_error,
                    details=f"Error in {report.window_title}",
                )

        return None

    def check_app_switch_event(self, report: ScreenObservationReport) -> Optional[ProactiveEvent]:
        """Check if the user switched foreground application, triggering conversational curiosity."""
        if not report or report.is_excluded or not self.config.proactive.app_switch_commentary:
            return None

        if self.state.active_mode not in (CompanionMode.COMPANION, CompanionMode.STUDY, CompanionMode.WORK_ASSISTANT):
            return None

        now = time.time()
        cur_proc = (report.process_name or "").lower()
        cur_title = report.window_title or ""
        prev_proc = (self.state.last_observed_process or "").lower()
        prev_title = self.state.last_observed_window or ""

        changed = False
        if cur_proc and prev_proc and cur_proc != prev_proc and cur_proc not in ("unknown", "desktop", "explorer.exe"):
            changed = True
        elif cur_title and prev_title and cur_title != prev_title and not prev_title.startswith("Unknown"):
            changed = True

        self.state.last_observed_process = cur_proc
        self.state.last_observed_window = cur_title

        if changed:
            # Avoid frequent chatter: minimum 60s between app-switch remarks
            if (now - self._last_app_switch_spoken_time) >= 60 and self.can_speak_proactively(priority=5):
                self._last_app_switch_spoken_time = now
                return ProactiveEvent(
                    event_id=f"evt-{uuid.uuid4().hex[:8]}",
                    event_type="app_switch",
                    priority=5,
                    title=report.window_title,
                    details=report.app_category,
                )

        return None

    def check_time_based_events(self) -> Optional[ProactiveEvent]:
        """Check for session milestone break reminders or idle check-ins."""
        now = time.time()

        # 1. Break reminder after 50 continuous minutes of work
        work_duration = now - self.state.session_start_time
        if work_duration >= 3000 and (now - self._last_break_reminder_time) >= 3000:
            if self.can_speak_proactively(priority=5):
                self._last_break_reminder_time = now
                return ProactiveEvent(
                    event_id=f"evt-{uuid.uuid4().hex[:8]}",
                    event_type="long_work_session",
                    priority=5,
                    title="Time for a short break",
                    details=f"Continuous session for {int(work_duration / 60)} minutes",
                )

        # 2. Autonomous Idle check-in in Companion or Study mode (initiates conversation without user speaking)
        last_activity = max(
            self.state.last_user_speech_time or self.state.session_start_time,
            self.state.last_companion_speech_time or self.state.session_start_time,
        )
        idle_thresh = self.config.proactive.idle_check_in_seconds
        if (now - last_activity) >= idle_thresh and self.state.active_mode in (CompanionMode.COMPANION, CompanionMode.STUDY):
            if (now - self._last_idle_spoken_time) >= idle_thresh and self.can_speak_proactively(priority=6):
                self._last_idle_spoken_time = now
                return ProactiveEvent(
                    event_id=f"evt-{uuid.uuid4().hex[:8]}",
                    event_type="check_in",
                    priority=6,
                    title="Spontaneous Check-in",
                    details="Harshan idle in companion mode",
                )

        return None

    def record_speech_delivered(self) -> None:
        """Mark that a proactive remark was voiced, updating timestamps and counts."""
        self.state.last_companion_speech_time = time.time()
        self.state.proactive_messages_today += 1
        self.state.hourly_proactive_count += 1
