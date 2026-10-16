"""Electorn Companion Mode — Persistent, Voice-Enabled, Screen-Aware AI Companion."""

from electorn.companion.activity_classifier import ActivityClassifier
from electorn.companion.cli import companion_app
from electorn.companion.interface import CompanionInterface
from electorn.companion.memory import MemoryEngine
from electorn.companion.personality import PersonalityEngine
from electorn.companion.proactive_scheduler import ProactiveScheduler
from electorn.companion.schema import (
    ActivityCategory,
    ActivityClassificationConfig,
    AffectionIntensity,
    BedtimeConfig,
    CompanionConfig,
    CompanionLifecycleState,
    CompanionMemoryItem,
    CompanionMode,
    CompanionState,
    ConversationFrequency,
    GreetingStyle,
    HumorLevel,
    MemoryCategory,
    PersonalityConfig,
    ProactiveEvent,
    ProactiveSpeechConfig,
    ScreenObservationConfig,
    ScreenObservationReport,
    StartupConfig,
    AvatarStyle,
    AvatarExpression,
    VideoCallConfig,
)
from electorn.companion.screen_observer import ScreenObservationEngine
from electorn.companion.startup import StartupManager
from electorn.companion.storage import CompanionStorage
from electorn.companion.supervisor import CompanionSupervisor
from electorn.companion.time_engine import TimeAwarenessEngine
from electorn.companion.tools import CompanionTools
from electorn.companion.video_server import VideoCallServer
from electorn.companion.vision_analyzer import VisionAnalyzer
from electorn.companion.voice_session import CompanionVoiceSession

__all__ = [
    "companion_app",
    "CompanionInterface",
    "MemoryEngine",
    "PersonalityEngine",
    "ProactiveScheduler",
    "ActivityClassifier",
    "ActivityCategory",
    "ActivityClassificationConfig",
    "AffectionIntensity",
    "BedtimeConfig",
    "CompanionConfig",
    "CompanionLifecycleState",
    "CompanionMemoryItem",
    "CompanionMode",
    "CompanionState",
    "ConversationFrequency",
    "GreetingStyle",
    "HumorLevel",
    "MemoryCategory",
    "PersonalityConfig",
    "ProactiveEvent",
    "ProactiveSpeechConfig",
    "ScreenObservationConfig",
    "ScreenObservationReport",
    "ScreenObservationEngine",
    "StartupConfig",
    "StartupManager",
    "CompanionStorage",
    "CompanionSupervisor",
    "TimeAwarenessEngine",
    "CompanionTools",
    "VisionAnalyzer",
    "CompanionVoiceSession",
    "AvatarStyle",
    "AvatarExpression",
    "VideoCallConfig",
    "VideoCallServer",
]
