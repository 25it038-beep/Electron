"""Electorn Companion Mode — Persistent, Voice-Enabled, Screen-Aware AI Companion."""

from electorn.companion.cli import companion_app
from electorn.companion.interface import CompanionInterface
from electorn.companion.memory import MemoryEngine
from electorn.companion.personality import PersonalityEngine
from electorn.companion.proactive_scheduler import ProactiveScheduler
from electorn.companion.schema import (
    AffectionIntensity,
    CompanionConfig,
    CompanionMemoryItem,
    CompanionMode,
    CompanionState,
    ConversationFrequency,
    GreetingStyle,
    HumorLevel,
    MemoryCategory,
    PersonalityConfig,
    ProactiveEvent,
    ScreenObservationConfig,
    ScreenObservationReport,
)
from electorn.companion.screen_observer import ScreenObservationEngine
from electorn.companion.storage import CompanionStorage
from electorn.companion.supervisor import CompanionSupervisor
from electorn.companion.tools import CompanionTools
from electorn.companion.vision_analyzer import VisionAnalyzer
from electorn.companion.voice_session import CompanionVoiceSession

__all__ = [
    "companion_app",
    "CompanionInterface",
    "MemoryEngine",
    "PersonalityEngine",
    "ProactiveScheduler",
    "AffectionIntensity",
    "CompanionConfig",
    "CompanionMemoryItem",
    "CompanionMode",
    "CompanionState",
    "ConversationFrequency",
    "GreetingStyle",
    "HumorLevel",
    "MemoryCategory",
    "PersonalityConfig",
    "ProactiveEvent",
    "ScreenObservationConfig",
    "ScreenObservationReport",
    "ScreenObservationEngine",
    "CompanionStorage",
    "CompanionSupervisor",
    "CompanionTools",
    "VisionAnalyzer",
    "CompanionVoiceSession",
]
