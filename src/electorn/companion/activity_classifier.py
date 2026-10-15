"""Activity classification engine with temporal accumulation and distraction tracking."""

from __future__ import annotations

import logging
import time
from typing import List, Optional, Tuple

from electorn.companion.schema import ActivityCategory, ActivityClassificationConfig

logger = logging.getLogger(__name__)


class ActivityClassifier:
    """Classifies foreground window activity over time to prevent snap judgments."""

    def __init__(self, config: Optional[ActivityClassificationConfig] = None) -> None:
        self.config = config or ActivityClassificationConfig()
        self.observation_history: List[Tuple[float, ActivityCategory, str]] = [] # (timestamp, category, app)
        self.current_activity: ActivityCategory = ActivityCategory.NEUTRAL
        self.current_activity_start_time: float = time.time()
        self.last_app_name: str = ""

    def classify_instant(self, window_title: str, process_name: str) -> Tuple[ActivityCategory, float]:
        """Infer instantaneous activity category and confidence from window metadata."""
        combined = f"{window_title.lower()} {process_name.lower()}".strip()

        # 1. Check Coding
        for app in self.config.productive_apps:
            if app in combined:
                # Distinguish coding videos from coding editor
                if any(v in combined for v in ["youtube", "video", "twitch"]):
                    return ActivityCategory.WATCHING_VIDEOS, 0.75
                return ActivityCategory.CODING, 0.95

        # 2. Check Studying
        for app in self.config.learning_apps:
            if app in combined:
                return ActivityCategory.STUDYING, 0.90

        # 3. Check Gaming
        for app in self.config.gaming_apps:
            if app in combined:
                return ActivityCategory.GAMING, 0.95

        # 4. Check Entertainment & Videos
        for app in self.config.entertainment_apps:
            if app in combined:
                if "youtube" in combined or "twitch" in combined or "netflix" in combined:
                    # Check if watching programming/study tutorial
                    if any(t in combined for t in ["tutorial", "python", "programming", "course", "lecture", "algorithm", "learn"]):
                        return ActivityCategory.STUDYING, 0.70
                    return ActivityCategory.WATCHING_VIDEOS, 0.85
                return ActivityCategory.ENTERTAINMENT, 0.85

        # 5. Check Communication
        if any(c in combined for c in ["slack", "teams", "discord", "whatsapp", "telegram", "outlook"]):
            return ActivityCategory.COMMUNICATION, 0.90

        # 6. Check Document / Reading
        if any(d in combined for d in ["word", "excel", "powerpoint", "notepad", "obsidian", "pdf", "acrobat"]):
            return ActivityCategory.DOCUMENT, 0.85

        # 7. Check Browsing
        if any(b in combined for b in ["chrome", "firefox", "msedge", "edge", "safari", "brave", "opera"]):
            return ActivityCategory.BROWSING, 0.60

        return ActivityCategory.NEUTRAL, 0.50

    def record_observation(
        self,
        window_title: str,
        process_name: str,
    ) -> Tuple[ActivityCategory, float, float, bool]:
        """Record an observation, accumulate duration, and check for sustained distraction.
        
        Returns:
            - sustained_category: ActivityCategory
            - confidence: float
            - sustained_duration_seconds: float
            - is_distracted: bool
        """
        now = time.time()
        instant_cat, instant_conf = self.classify_instant(window_title, process_name)
        self.observation_history.append((now, instant_cat, process_name))

        # Keep rolling window of last 20 observations (last ~5 minutes)
        if len(self.observation_history) > 20:
            self.observation_history = self.observation_history[-20:]

        # Check if activity changed
        if self.current_activity == ActivityCategory.NEUTRAL:
            self.current_activity = instant_cat
            self.current_activity_start_time = now
            self.last_app_name = process_name
        elif instant_cat != self.current_activity:
            # Require at least 2 consecutive observations before confirming activity shift
            recent_same = sum(1 for _, cat, _ in self.observation_history[-2:] if cat == instant_cat)
            if recent_same >= 2:
                self.current_activity = instant_cat
                self.current_activity_start_time = now
                self.last_app_name = process_name

        sustained_duration = max(0.0, now - self.current_activity_start_time)

        # Distraction criteria:
        # User in WATCHING_VIDEOS, ENTERTAINMENT, or GAMING for > distraction_threshold_seconds (e.g. 40 min)
        is_distracted = False
        if self.current_activity in (ActivityCategory.WATCHING_VIDEOS, ActivityCategory.ENTERTAINMENT, ActivityCategory.GAMING):
            if sustained_duration >= self.config.distraction_threshold_seconds:
                is_distracted = True

        return self.current_activity, instant_conf, sustained_duration, is_distracted
