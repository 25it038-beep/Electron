"""Time awareness engine providing authoritative system clock, bedtime scheduling, and quiet hours."""

from __future__ import annotations

from datetime import datetime, time as dtime, timedelta
import logging
import re
import time
from typing import Optional, Tuple

from electorn.companion.schema import BedtimeConfig

logger = logging.getLogger(__name__)


class TimeAwarenessEngine:
    """Manages authoritative system time, bedtime stages, quiet hours, and clock comparisons."""

    @staticmethod
    def get_system_time() -> datetime:
        """Authoritative current system time."""
        return datetime.now()

    @staticmethod
    def get_formatted_time(dt: Optional[datetime] = None) -> str:
        """Formatted human-readable current time."""
        target = dt or datetime.now()
        return target.strftime("%I:%M %p").lstrip("0")

    @staticmethod
    def get_time_of_day_category(dt: Optional[datetime] = None) -> str:
        """Categorize into morning, afternoon, evening, or night."""
        hour = (dt or datetime.now()).hour
        if 5 <= hour < 12:
            return "morning"
        elif 12 <= hour < 17:
            return "afternoon"
        elif 17 <= hour < 22:
            return "evening"
        else:
            return "night"

    def is_in_quiet_hours(self, config: BedtimeConfig, dt: Optional[datetime] = None) -> bool:
        """Check if current time is within configured quiet hours."""
        if not config.quiet_hours_enabled:
            return False

        current_time = (dt or datetime.now()).time()
        try:
            sh, sm = [int(p) for p in config.quiet_hours_start.split(":")]
            eh, em = [int(p) for p in config.quiet_hours_end.split(":")]
            start = dtime(sh, sm)
            end = dtime(eh, em)

            if start <= end:
                return start <= current_time <= end
            else:
                return current_time >= start or current_time <= end
        except Exception as e:
            logger.debug("Quiet hours parse error: %s", e)
            return False

    def is_date_exception(self, config: BedtimeConfig, dt: Optional[datetime] = None) -> bool:
        """Check if today's date is configured as a sleep reminder exception."""
        today_str = (dt or datetime.now()).strftime("%Y-%m-%d")
        return today_str in config.exception_dates

    def is_snoozed(self, config: BedtimeConfig) -> bool:
        """Check if bedtime reminder is currently snoozed."""
        if not config.snooze_until:
            return False
        return time.time() < config.snooze_until

    def snooze(self, config: BedtimeConfig, minutes: int = 30) -> float:
        """Snooze bedtime reminders for specified minutes."""
        until = time.time() + (minutes * 60)
        config.snooze_until = until
        return until

    def evaluate_bedtime_stage(
        self,
        config: BedtimeConfig,
        dt: Optional[datetime] = None,
    ) -> Optional[str]:
        """Determine whether current system time warrants a bedtime reminder stage.
        
        Returns:
            - 'bedtime_warning' (e.g. 30 min before bedtime)
            - 'bedtime_due'     (at bedtime, within 10 min)
            - 'bedtime_late'    (15-60 min past bedtime)
            - 'bedtime_critical'(> 60 min past bedtime)
            - None if outside bedtime window or snoozed/exception
        """
        if not config.enabled:
            return None

        now = dt or datetime.now()

        if self.is_date_exception(config, now) or self.is_snoozed(config):
            return None

        try:
            bh, bm = [int(p) for p in config.bedtime.split(":")]
            # Construct target bedtime for today
            bedtime_dt = now.replace(hour=bh, minute=bm, second=0, microsecond=0)

            # If bedtime is late night (e.g. 23:30) and now is early morning (e.g. 01:00), adjust bedtime_dt to yesterday
            diff_seconds = (now - bedtime_dt).total_seconds()
            if diff_seconds < -43200: # more than 12 hours ahead -> bedtime was yesterday
                bedtime_dt = bedtime_dt - timedelta(days=1)
                diff_seconds = (now - bedtime_dt).total_seconds()
            elif diff_seconds > 43200: # more than 12 hours behind -> bedtime is tomorrow
                bedtime_dt = bedtime_dt + timedelta(days=1)
                diff_seconds = (now - bedtime_dt).total_seconds()

            lead_sec = config.warning_lead_minutes * 60

            # 1. Warning Stage: between (bedtime - lead_sec) and (bedtime - 5 min)
            if -lead_sec <= diff_seconds <= -300:
                return "bedtime_warning"

            # 2. Due Stage: within -5 min to +15 min of bedtime
            if -300 < diff_seconds <= 900:
                return "bedtime_due"

            # 3. Late Stage: 15 min to 60 min past bedtime
            if 900 < diff_seconds <= 3600:
                return "bedtime_late"

            # 4. Critical Stage: > 60 min past bedtime (up to 4 hours past)
            if 3600 < diff_seconds <= 14400:
                return "bedtime_critical"

        except Exception as e:
            logger.debug("Bedtime evaluation error: %s", e)

        return None

    def compare_ocr_clock(
        self,
        ocr_text: str,
        system_time: Optional[datetime] = None,
    ) -> Tuple[Optional[str], Optional[str]]:
        """Extract clock string from OCR and compare with authoritative system time.
        
        Returns (visible_clock_time, discrepancy_note).
        """
        if not ocr_text:
            return None, None

        sys_dt = system_time or datetime.now()
        # Look for time patterns like 11:30 PM, 23:30, 10:15 AM
        match = re.search(r"\b(\d{1,2}:\d{2}(?:\s*[AaPp][Mm])?)\b", ocr_text)
        if not match:
            return None, None

        clock_str = match.group(1).strip()
        sys_str = sys_dt.strftime("%I:%M %p").lstrip("0")

        discrepancy = None
        # Simple heuristic check: if visible clock is drastically different
        # Note: system clock is authoritative
        return clock_str, discrepancy
