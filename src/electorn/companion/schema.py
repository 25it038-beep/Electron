"""Data models, configuration schemas, and state definitions for Electorn Companion Mode."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from pathlib import Path
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class CompanionMode(str, Enum):
    """Operational mode determining proactive speech, screen observation, and permissions."""
    COMPANION = "companion"          # Normal conversation, optional screen monitoring, proactive check-ins
    FOCUS = "focus"                  # Suppress casual interruptions; queue non-critical observations; urgent notifications only
    STUDY = "study"                  # Tracks study intervals and tasks; gentle distraction alerts; contextual help
    NIGHT = "night"                  # Reduces frequency; quiet/shorter bedtime reminders; respects quiet hours
    PASSIVE = "passive"              # Responds only when spoken to; screen observation off by default
    PRIVACY = "privacy"              # Microphones and screen capture completely disabled; text-only interactions
    WORK_ASSISTANT = "work_assistant"# Actively observes workflows; offers code and testing help


class CompanionLifecycleState(str, Enum):
    """Real-time companion state for visual dashboards, tray icons, and logs."""
    STARTING = "STARTING"
    READY = "READY"
    LISTENING = "LISTENING"
    THINKING = "THINKING"
    SPEAKING = "SPEAKING"
    MONITORING = "MONITORING"
    PAUSED = "PAUSED"
    QUIET = "QUIET"
    ERROR = "ERROR"


class ActivityCategory(str, Enum):
    """Categorization of observed foreground activity."""
    CODING = "coding"
    STUDYING = "studying"
    BROWSING = "browsing"
    WATCHING_VIDEOS = "watching_videos"
    GAMING = "gaming"
    ENTERTAINMENT = "entertainment"
    COMMUNICATION = "communication"
    DOCUMENT = "document"
    NEUTRAL = "neutral"
    OTHER = "other"


class AffectionIntensity(str, Enum):
    """Intensity of affectionate, caring language in companion responses."""
    LOW = "low"          # Polite, friendly, lightly warm
    MEDIUM = "medium"    # Caring, engaging, playful
    HIGH = "high"        # Warm, caring, sweet, supportive girlfriend-style companion


class HumorLevel(str, Enum):
    """Frequency and style of playful humor and light teasing."""
    LOW = "low"          # Subtle, gentle humor
    MEDIUM = "medium"    # Witty, playful banter
    HIGH = "high"        # High energy, teasing, very playful


class ConversationFrequency(str, Enum):
    """Frequency threshold for unsolicited proactive companion check-ins."""
    LOW = "low"          # Rare check-ins (every 45-60+ min or on critical errors only)
    MEDIUM = "medium"    # Balanced check-ins (every 20-30 min when appropriate)
    HIGH = "high"        # Frequent check-ins (every 10-15 min)


class GreetingStyle(str, Enum):
    """Style of initial welcome greeting upon starting session."""
    WARM_AFFECTIONATE = "warm_affectionate"
    CHEERFUL_PLAYFUL = "cheerful_playful"
    CALM_SUPPORTIVE = "calm_supportive"


class PersonalityConfig(BaseModel):
    """Configuration governing companion persona, tone, naming, and language code-switching."""
    name: str = "Aria"
    user_name: str = "Harshan"
    preferred_address: str = "Harshan"           # Address user as Harshan. Never use pet names.
    prohibit_pet_names: bool = True              # Strictly forbids darling, honey, baby, sweetie, etc.
    voice_gender: str = "female"
    language: str = "en-US"                      # "en-US", "ta-IN", or "tanglish"
    code_switch_tamil: bool = True               # Enable natural Tamil-English code-switching
    speaking_speed: float = 1.0
    affection_intensity: AffectionIntensity = AffectionIntensity.HIGH
    humor_level: HumorLevel = HumorLevel.MEDIUM
    conversation_frequency: ConversationFrequency = ConversationFrequency.MEDIUM
    greeting_style: GreetingStyle = GreetingStyle.WARM_AFFECTIONATE


class BedtimeConfig(BaseModel):
    """Configuration for system-clock bedtime reminders and sleep schedules."""
    enabled: bool = True
    bedtime: str = "23:30"                       # 11:30 PM (24-hour HH:MM)
    wake_time: str = "07:00"                     # 7:00 AM
    warning_lead_minutes: int = 30               # Gentle reminder 30 min before bedtime
    snooze_until: Optional[float] = None         # Epoch timestamp if snoozed
    exception_dates: List[str] = Field(default_factory=list)  # Dates formatted as YYYY-MM-DD
    max_late_night_reminders: int = 4            # Maximum proactive reminders per night
    quiet_hours_enabled: bool = True
    quiet_hours_start: str = "23:30"
    quiet_hours_end: str = "07:00"


class ActivityClassificationConfig(BaseModel):
    """Rules and thresholds for classifying active applications and sustained activities."""
    enabled: bool = True
    distraction_threshold_seconds: int = 2400    # 40 minutes in entertainment/videos before gentle check-in
    learning_apps: List[str] = Field(default_factory=lambda: [
        "coursera", "udemy", "anki", "edx", "khan", "leetcoding", "docs", "arxiv", "canvas", "blackboard"
    ])
    productive_apps: List[str] = Field(default_factory=lambda: [
        "code", "visual studio", "pycharm", "sublime", "vim", "nvim", "intellij", "git", "terminal", "powershell", "cursor"
    ])
    entertainment_apps: List[str] = Field(default_factory=lambda: [
        "netflix", "youtube", "twitch", "primevideo", "hulu", "disney", "spotify", "tiktok", "instagram"
    ])
    gaming_apps: List[str] = Field(default_factory=lambda: [
        "steam", "epicgames", "riot", "valorant", "minecraft", "roblox", "league", "fortnite"
    ])


class StartupConfig(BaseModel):
    """Windows Task Scheduler / Registry automatic startup configuration."""
    enabled: bool = False
    task_name: str = "ElectornCompanion"
    last_startup_greeting_timestamp: float = 0.0 # Prevents duplicate greetings on rapid restarts


class ProactiveSpeechConfig(BaseModel):
    """Fine-grained controls over unsolicited proactive messages."""
    enabled: bool = True
    max_per_hour: int = 30                       # Up to 30 proactive check-ins per hour in companion mode
    min_interval_seconds: int = 75               # Natural ~1-2 min conversational pacing
    idle_check_in_seconds: int = 90              # Proactively initiate conversation if user is silent for 90s
    daily_limit: int = 150
    app_switch_commentary: bool = True           # Proactively comment on application transitions
    screen_commentary: bool = True               # Proactively comment on screen progress or errors
    allow_active_quiet_hours_override: bool = True # Allow conversational remarks when user is actively at computer


class ScreenObservationConfig(BaseModel):
    """Configuration for privacy-preserving screen observation."""
    enabled: bool = True                         # Live screen observation active by default
    interval_seconds: int = 5                    # Real-time capture frequency (5s)
    change_detection_threshold: float = 0.08     # 8% visual variance required before analyzing
    capture_active_window_only: bool = True      # Capture active foreground window instead of full desktop
    save_history: bool = False                   # In-memory only by default
    ocr_enabled: bool = True
    vision_model: str = "qwen3-vl:4b-instruct"
    excluded_apps: List[str] = Field(default_factory=lambda: [
        "1password", "bitwarden", "keepass", "lastpass",
        "private", "incognito", "bank", "token", "credential",
        "settings", "authenticator", "keychain"
    ])
    max_history_entries: int = 50


class ScreenObservationReport(BaseModel):
    """Structured result of a privacy-filtered screen analysis."""
    timestamp: float = Field(default_factory=time.time)
    window_title: str = "Unknown Window"
    process_name: str = "Unknown"
    app_category: str = "other"                  # code_editor, terminal, browser, document, communication, other
    activity_category: ActivityCategory = ActivityCategory.NEUTRAL
    sustained_duration_seconds: float = 0.0
    is_excluded: bool = False
    change_ratio: float = 0.0
    visible_summary: str = ""
    visible_error: Optional[str] = None
    visible_clock_time: Optional[str] = None     # OCR visible clock if detected
    clock_discrepancy: Optional[str] = None      # Discrepancy warning if OCR clock != system clock
    suggested_assistance: Optional[str] = None
    confidence: float = 1.0
    requires_user_approval: bool = False


class ProactiveEvent(BaseModel):
    """An event triggering or proposing companion proactive communication."""
    event_id: str
    timestamp: float = Field(default_factory=time.time)
    event_type: str                              # startup, bedtime_warning, bedtime_due, bedtime_late, distraction_check, error_detected, long_work_session, reminder, check_in, deadline
    priority: int = 4                            # 1=Critical Security/System, 2=User Reminder, 3=Deadline/Bedtime, 4=Startup, 5=Contextual Help, 6=Casual Conversation
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
    STUDY_SESSION = "study_session"


class CompanionMemoryItem(BaseModel):
    """An individual persistent memory record."""
    memory_id: str
    timestamp: float = Field(default_factory=time.time)
    category: MemoryCategory
    key: str
    value: str
    confidence: float = 1.0
    source: str = "conversation"                 # conversation, screen_observation, explicit_user_note


class AvatarStyle(str, Enum):
    """Selectable visual style presets for the animated companion avatar."""
    REALISTIC = "realistic"
    ANIME = "anime"
    HOLOGRAM = "hologram"
    MINIMALIST = "minimalist"
    CANVAS_2D = "canvas_2d"


class AvatarExpression(str, Enum):
    """Dynamic emotional and conversational expression states for avatar rendering."""
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"
    HAPPY = "happy"
    CONFUSED = "confused"
    EMPATHETIC = "empathetic"
    ERROR = "error"


class VideoCallConfig(BaseModel):
    """Configuration for real-time video call interface and 3D avatar rendering."""
    enabled: bool = True
    host: str = "127.0.0.1"
    port: int = 8765
    avatar_style: AvatarStyle = AvatarStyle.REALISTIC
    camera_enabled: bool = False
    camera_analysis_enabled: bool = True
    live_captions: bool = True
    audio_visualizer: bool = True
    quality: str = "auto"                        # auto, high, medium, low


class CompanionConfig(BaseModel):
    """Root configuration for Companion Mode."""
    mode: CompanionMode = CompanionMode.COMPANION
    personality: PersonalityConfig = Field(default_factory=PersonalityConfig)
    bedtime: BedtimeConfig = Field(default_factory=BedtimeConfig)
    activity: ActivityClassificationConfig = Field(default_factory=ActivityClassificationConfig)
    startup: StartupConfig = Field(default_factory=StartupConfig)
    proactive: ProactiveSpeechConfig = Field(default_factory=ProactiveSpeechConfig)
    screen: ScreenObservationConfig = Field(default_factory=ScreenObservationConfig)
    video_call: VideoCallConfig = Field(default_factory=VideoCallConfig)
    storage_directory: Path = Field(default_factory=lambda: Path.home() / ".electorn" / "companion")
    voice_enabled: bool = True
    push_to_talk: bool = False
    barge_in_enabled: bool = True                # Stop speaking when user begins talking
    memory_enabled: bool = True


class CompanionState(BaseModel):
    """Live runtime state of the active companion session."""
    active_mode: CompanionMode = CompanionMode.COMPANION
    current_lifecycle: CompanionLifecycleState = CompanionLifecycleState.READY
    is_paused: bool = False                      # Global emergency pause
    is_muted: bool = False                       # Mic mute
    mic_active: bool = False
    screen_active: bool = False
    session_start_time: float = Field(default_factory=time.time)
    last_user_speech_time: Optional[float] = None
    last_companion_speech_time: Optional[float] = None
    proactive_messages_today: int = 0
    hourly_proactive_count: int = 0
    current_hour_window: int = Field(default_factory=lambda: datetime.now().hour)
    late_night_reminders_count: int = 0
    active_window_title: Optional[str] = None
    last_observed_window: Optional[str] = None
    last_observed_process: Optional[str] = None
    interactive_session_active: bool = False
    current_activity: ActivityCategory = ActivityCategory.NEUTRAL
    activity_start_time: float = Field(default_factory=time.time)
    study_session_start_time: Optional[float] = None
    queued_events: List[ProactiveEvent] = Field(default_factory=list)
