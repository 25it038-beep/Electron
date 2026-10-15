"""Data models, configuration schemas, and state definitions for Electorn Companion Mode."""

from __future__ import annotations

import time
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class CompanionMode(str, Enum):
    """Operational mode determining proactive speech, screen observation, and permissions."""
    PASSIVE = "passive"              # Responds only when spoken to; screen observation off by default
    COMPANION = "companion"          # Persistent voice interaction, optional screen observation, warm proactive check-ins
    FOCUS = "focus"                  # Minimal interruptions; queues non-critical observations; urgent notifications only
    WORK_ASSISTANT = "work_assistant"# Actively observes authorized workflows; offers contextual help, test & error assistance
    PRIVACY = "privacy"              # Microphones and screen capture completely disabled; text-only interactions


class AffectionIntensity(str, Enum):
    """Intensity of affectionate, caring language in companion responses."""
    LOW = "low"          # Polite, friendly, lightly warm
    MEDIUM = "medium"    # Caring, affectionate, engaging, playful
    HIGH = "high"        # Deeply warm, caring, sweet, girlfriend-style affection


class HumorLevel(str, Enum):
    """Frequency and style of playful humor and light teasing."""
    LOW = "low"          # Subtle, gentle humor
    MEDIUM = "medium"    # Witty, playful, charming teasing
    HIGH = "high"        # High energy, teasing, very playful


class ConversationFrequency(str, Enum):
    """Frequency threshold for unsolicited proactive companion check-ins."""
    LOW = "low"          # Rare check-ins (every 60+ min or on critical errors only)
    MEDIUM = "medium"    # Balanced check-ins (every 30-45 min or on notable events)
    HIGH = "high"        # Frequent check-ins (every 15-20 min when appropriate)


class GreetingStyle(str, Enum):
    """Style of initial welcome greeting upon starting session."""
    WARM_AFFECTIONATE = "warm_affectionate"
    CHEERFUL_PLAYFUL = "cheerful_playful"
    CALM_SUPPORTIVE = "calm_supportive"


class PersonalityConfig(BaseModel):
    """Configuration governing companion persona, tone, naming, and language code-switching."""
    name: str = "Aria"
    preferred_address: str = "Darling"           # How companion addresses the user (Darling, Babe, Dear, etc.)
    user_name: str = "Harshan"
    voice_gender: str = "female"
    language: str = "en-US"                      # "en-US", "ta-IN", or "tanglish"
    code_switch_tamil: bool = True               # Enable natural Tamil-English code-switching
    speaking_speed: float = 1.0
    affection_intensity: AffectionIntensity = AffectionIntensity.HIGH
    humor_level: HumorLevel = HumorLevel.MEDIUM
    conversation_frequency: ConversationFrequency = ConversationFrequency.MEDIUM
    proactive_daily_limit: int = 35              # Maximum unsolicited observations per day
    quiet_hours_enabled: bool = True
    quiet_hours_start: str = "22:30"             # 10:30 PM
    quiet_hours_end: str = "08:00"               # 8:00 AM
    greeting_style: GreetingStyle = GreetingStyle.WARM_AFFECTIONATE
    min_interval_seconds: int = 600              # Minimum 10 minutes between unsolicited proactive statements


class ScreenObservationConfig(BaseModel):
    """Configuration for privacy-preserving screen observation."""
    enabled: bool = False                        # Explicit opt-in required
    interval_seconds: int = 15                   # Capture frequency
    change_detection_threshold: float = 0.08     # 8% visual variance required before analyzing
    capture_active_window_only: bool = True      # Capture active foreground window instead of full desktop
    save_history: bool = False                   # In-memory only by default
    ocr_enabled: bool = True
    vision_model: str = "qwen3-vl:4b-instruct"
    excluded_apps: List[str] = Field(default_factory=lambda: [
        "1password", "bitwarden", "keepass", "lastpass",
        "private", "incognito", "bank", "token", "credential",
        "settings", "steam", "authenticator"
    ])
    max_history_entries: int = 50


class ScreenObservationReport(BaseModel):
    """Structured result of a privacy-filtered screen analysis."""
    timestamp: float = Field(default_factory=time.time)
    window_title: str = "Unknown Window"
    process_name: str = "Unknown"
    app_category: str = "other"                  # code_editor, terminal, browser, document, communication, other
    is_excluded: bool = False
    change_ratio: float = 0.0
    visible_summary: str = ""
    visible_error: Optional[str] = None
    suggested_assistance: Optional[str] = None
    confidence: float = 1.0
    requires_user_approval: bool = False


class ProactiveEvent(BaseModel):
    """An event triggering or proposing companion proactive communication."""
    event_id: str
    timestamp: float = Field(default_factory=time.time)
    event_type: str                              # startup, error_detected, long_work_session, document_open, reminder, check_in
    priority: str = "medium"                     # low, medium, high, urgent
    title: str = ""
    details: str = ""
    suggested_speech: str = ""
    delivered: bool = False
    delivered_timestamp: Optional[float] = None


class MemoryCategory(str, Enum):
    """Categorical segregation of stored memory records."""
    USER_PREFERENCE = "user_preference"
    CONVERSATION_SUMMARY = "conversation_summary"
    ACTIVE_PROJECT = "active_project"
    OBSERVED_WORK_STYLE = "observed_work_style"
    TASK_COMMITMENT = "task_commitment"


class CompanionMemoryItem(BaseModel):
    """An individual persistent memory record."""
    memory_id: str
    timestamp: float = Field(default_factory=time.time)
    category: MemoryCategory
    key: str
    value: str
    confidence: float = 1.0
    source: str = "conversation"                 # conversation, screen_observation, explicit_user_note


class CompanionConfig(BaseModel):
    """Root configuration for Companion Mode."""
    mode: CompanionMode = CompanionMode.COMPANION
    personality: PersonalityConfig = Field(default_factory=PersonalityConfig)
    screen: ScreenObservationConfig = Field(default_factory=ScreenObservationConfig)
    storage_directory: Path = Field(default_factory=lambda: Path.home() / ".electorn" / "companion")
    voice_enabled: bool = True
    push_to_talk: bool = False
    barge_in_enabled: bool = True                # Stop speaking when user begins talking
    memory_enabled: bool = True


class CompanionState(BaseModel):
    """Live runtime state of the active companion session."""
    active_mode: CompanionMode = CompanionMode.COMPANION
    is_paused: bool = False                      # Global emergency pause
    mic_active: bool = False
    screen_active: bool = False
    session_start_time: float = Field(default_factory=time.time)
    last_user_speech_time: Optional[float] = None
    last_companion_speech_time: Optional[float] = None
    proactive_messages_today: int = 0
    queued_events: List[ProactiveEvent] = Field(default_factory=list)
    active_window_title: Optional[str] = None
