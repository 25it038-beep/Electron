"""Automated unit and integration test suite for Electorn Companion Mode."""

from datetime import datetime, timezone
import json
from pathlib import Path
import time
from unittest.mock import MagicMock, patch
import pytest
from typer.testing import CliRunner

from electorn.companion.activity_classifier import ActivityClassifier
from electorn.companion.cli import companion_app
from electorn.companion.interface import CompanionInterface
from electorn.companion.memory import MemoryEngine
from electorn.companion.personality import PersonalityEngine
from electorn.companion.proactive_scheduler import ProactiveScheduler
from electorn.companion.schema import (
    ActivityCategory,
    AffectionIntensity,
    BedtimeConfig,
    CompanionConfig,
    CompanionLifecycleState,
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
from electorn.companion.startup import StartupManager
from electorn.companion.storage import CompanionStorage
from electorn.companion.supervisor import CompanionSupervisor
from electorn.companion.time_engine import TimeAwarenessEngine
from electorn.companion.tools import CompanionTools
from electorn.companion.vision_analyzer import VisionAnalyzer
from electorn.companion.voice_session import CompanionVoiceSession

runner = CliRunner()


# =============================================================================
# 1. PERSONAL IDENTITY & NO-PET-NAME TESTS
# =============================================================================

def test_personality_preferred_name_harshan():
    """Verify system prompt mandates addressing user as Harshan and forbids pet names."""
    cfg = PersonalityConfig(user_name="Harshan", preferred_address="Harshan", prohibit_pet_names=True)
    engine = PersonalityEngine(cfg)
    prompt = engine.build_system_prompt(current_mode=CompanionMode.COMPANION)

    assert "Harshan" in prompt
    assert "NEVER use pet names" in prompt
    assert "darling" in prompt.lower()  # in the prohibition rule list


def test_personality_strictly_scrubs_pet_names_from_llm():
    """Verify sanitizer strips darling/honey/baby and substitutes Harshan."""
    cfg = PersonalityConfig(user_name="Harshan", prohibit_pet_names=True)
    engine = PersonalityEngine(cfg)

    raw_output = "Good night, darling! Take care, honey."
    sanitized = engine.sanitize_llm_response(raw_output)

    assert "darling" not in sanitized.lower()
    assert "honey" not in sanitized.lower()
    assert "Harshan" in sanitized


def test_personality_greetings_use_harshan():
    """Verify greetings include Harshan and never pet names."""
    cfg = PersonalityConfig(user_name="Harshan", preferred_address="Harshan")
    engine = PersonalityEngine(cfg)

    for _ in range(5):
        greeting = engine.generate_greeting()
        assert "Harshan" in greeting
        assert "darling" not in greeting.lower()
        assert "honey" not in greeting.lower()
        assert "baby" not in greeting.lower()


def test_personality_mode_prompts():
    """Verify study and night modes inject specific instructions."""
    cfg = PersonalityConfig(user_name="Harshan")
    engine = PersonalityEngine(cfg)

    study_prompt = engine.build_system_prompt(current_mode=CompanionMode.STUDY)
    assert "STUDY MODE" in study_prompt

    night_prompt = engine.build_system_prompt(current_mode=CompanionMode.NIGHT)
    assert "NIGHT MODE" in night_prompt


# =============================================================================
# 2. TIME AWARENESS & BEDTIME STAGES TESTS
# =============================================================================

def test_time_engine_system_clock_authoritative():
    """Verify system clock is authoritative."""
    engine = TimeAwarenessEngine()
    sys_time = engine.get_system_time()
    assert isinstance(sys_time, datetime)
    formatted = engine.get_formatted_time(sys_time)
    assert ":" in formatted


def test_time_engine_bedtime_warning_stage():
    """Verify bedtime warning triggers 30 minutes before configured bedtime."""
    engine = TimeAwarenessEngine()
    cfg = BedtimeConfig(enabled=True, bedtime="23:30", warning_lead_minutes=30)

    # Test time at 23:05 (25 min before bedtime -> warning stage)
    test_dt = datetime(2026, 10, 15, 23, 5, 0)
    stage = engine.evaluate_bedtime_stage(cfg, dt=test_dt)
    assert stage == "bedtime_warning"


def test_time_engine_bedtime_due_and_late_stages():
    """Verify bedtime due and late stages."""
    engine = TimeAwarenessEngine()
    cfg = BedtimeConfig(enabled=True, bedtime="23:30")

    # Due (at 23:32)
    due_dt = datetime(2026, 10, 15, 23, 32, 0)
    assert engine.evaluate_bedtime_stage(cfg, dt=due_dt) == "bedtime_due"

    # Late (at 23:55)
    late_dt = datetime(2026, 10, 15, 23, 55, 0)
    assert engine.evaluate_bedtime_stage(cfg, dt=late_dt) == "bedtime_late"


def test_time_engine_snooze_and_exception_dates():
    """Verify snoozing and date exceptions suppress bedtime evaluation."""
    engine = TimeAwarenessEngine()
    cfg = BedtimeConfig(enabled=True, bedtime="23:30", exception_dates=["2026-10-15"])

    test_dt = datetime(2026, 10, 15, 23, 35, 0)
    # Blocked by exception date
    assert engine.evaluate_bedtime_stage(cfg, dt=test_dt) is None

    # Snooze test
    cfg.exception_dates = []
    engine.snooze(cfg, minutes=30)
    assert engine.is_snoozed(cfg) is True
    assert engine.evaluate_bedtime_stage(cfg, dt=test_dt) is None


# =============================================================================
# 3. ACTIVITY CLASSIFICATION & DISTRACTION TESTS
# =============================================================================

def test_activity_classification_categories():
    """Verify instant classification of productive, learning, and entertainment apps."""
    classifier = ActivityClassifier()

    cat, _ = classifier.classify_instant("main.py - Visual Studio Code", "code.exe")
    assert cat == ActivityCategory.CODING

    cat, _ = classifier.classify_instant("Coursera Machine Learning", "chrome.exe")
    assert cat == ActivityCategory.STUDYING

    cat, _ = classifier.classify_instant("YouTube - Funny Cats", "chrome.exe")
    assert cat == ActivityCategory.WATCHING_VIDEOS

    # Python tutorial on YouTube classified as study
    cat, _ = classifier.classify_instant("Python Tutorial for Beginners - YouTube", "msedge.exe")
    assert cat == ActivityCategory.STUDYING

    cat, _ = classifier.classify_instant("Steam", "steam.exe")
    assert cat == ActivityCategory.GAMING


def test_activity_sustained_distraction_tracking():
    """Verify sustained duration accumulates and flags distraction past threshold."""
    classifier = ActivityClassifier()
    classifier.config.distraction_threshold_seconds = 60  # Shortened for test

    # Simulate 2 observations of YouTube
    cat, conf, dur, is_dist = classifier.record_observation("YouTube - Random Memes", "chrome.exe")
    assert cat == ActivityCategory.WATCHING_VIDEOS
    assert is_dist is False

    # Simulate time passing > 60s
    classifier.current_activity_start_time -= 70
    cat, conf, dur, is_dist = classifier.record_observation("YouTube - Random Memes", "chrome.exe")
    assert is_dist is True


# =============================================================================
# 4. STARTUP MANAGER & SINGLE INSTANCE TESTS
# =============================================================================

def test_startup_manager_instance_lock(tmp_path: Path):
    """Verify single instance lock prevents duplicate processes."""
    mgr = StartupManager(lock_dir=tmp_path)
    assert mgr.acquire_instance_lock() is True
    # Second acquisition fails
    mgr2 = StartupManager(lock_dir=tmp_path)
    assert mgr2.acquire_instance_lock() is False
    mgr.release_instance_lock()
    assert mgr2.acquire_instance_lock() is True
    mgr2.release_instance_lock()


# =============================================================================
# 5. PROACTIVE SCHEDULER & ANTI-ANNOYANCE TESTS
# =============================================================================

def test_proactive_scheduler_bedtime_event():
    """Verify scheduler triggers proactive bedtime event at bedtime."""
    cfg = CompanionConfig()
    cfg.bedtime.bedtime = "23:30"
    state = CompanionState(active_mode=CompanionMode.COMPANION)
    sched = ProactiveScheduler(cfg, state)

    # Mock time_engine evaluate to bedtime_warning
    sched.time_engine.evaluate_bedtime_stage = MagicMock(return_value="bedtime_warning")
    sched.time_engine.get_formatted_time = MagicMock(return_value="11:05 PM")

    evt = sched.check_bedtime_event()
    assert evt is not None
    assert evt.event_type == "bedtime_warning"
    assert evt.priority == 3


def test_proactive_scheduler_hourly_rate_limit():
    """Verify scheduler respects max_per_hour limit."""
    cfg = CompanionConfig()
    cfg.proactive.max_per_hour = 2
    state = CompanionState(
        active_mode=CompanionMode.COMPANION,
        hourly_proactive_count=2,
    )
    sched = ProactiveScheduler(cfg, state)

    # Casual priority 5 blocked
    assert sched.can_speak_proactively(priority=5) is False
    # Critical priority 1 passes
    assert sched.can_speak_proactively(priority=1) is True


def test_proactive_scheduler_app_switch_event():
    """Verify application switch triggers proactive event."""
    cfg = CompanionConfig()
    state = CompanionState(
        active_mode=CompanionMode.COMPANION,
        last_observed_process="chrome.exe",
        last_observed_window="Google Chrome",
    )
    sched = ProactiveScheduler(cfg, state)
    report = ScreenObservationReport(
        window_title="main.py - Visual Studio Code",
        process_name="code.exe",
        app_category="code_editor",
        activity_category=ActivityCategory.CODING,
    )
    evt = sched.check_app_switch_event(report)
    assert evt is not None
    assert evt.event_type == "app_switch"
    assert "Visual Studio Code" in evt.title


def test_proactive_scheduler_idle_checkin_event():
    """Verify idle silence triggers autonomous conversation starter."""
    cfg = CompanionConfig()
    cfg.proactive.idle_check_in_seconds = 30
    cfg.proactive.min_interval_seconds = 30
    past = time.time() - 40
    state = CompanionState(
        active_mode=CompanionMode.COMPANION,
        session_start_time=past,
        last_user_speech_time=past,
        last_companion_speech_time=past,
    )
    sched = ProactiveScheduler(cfg, state)
    evt = sched.check_time_based_events()
    assert evt is not None
    assert evt.event_type == "check_in"


# =============================================================================
# 6. SUPERVISOR & VOICE COMMANDS TESTS
# =============================================================================

def test_supervisor_voice_command_what_am_i_doing(tmp_path: Path):
    """Verify voice command 'what am I doing right now' returns activity."""
    cfg = CompanionConfig(storage_directory=tmp_path)
    cfg.personality.user_name = "Harshan"
    supervisor = CompanionSupervisor(config=cfg)
    supervisor.state.active_window_title = "VS Code"
    supervisor.state.current_activity = ActivityCategory.CODING

    reply = supervisor.process_user_input("What am I doing right now?")
    assert "Harshan" in reply
    assert "coding" in reply.lower()


def test_supervisor_voice_command_study_mode(tmp_path: Path):
    """Verify voice command 'study mode' switches mode to STUDY."""
    cfg = CompanionConfig(storage_directory=tmp_path)
    supervisor = CompanionSupervisor(config=cfg)

    reply = supervisor.process_user_input("stay quiet while I study")
    assert supervisor.state.active_mode == CompanionMode.STUDY
    assert "Study Mode" in reply


def test_supervisor_voice_mute_command(tmp_path: Path):
    """Verify voice command 'stop listening' mutes microphone."""
    cfg = CompanionConfig(storage_directory=tmp_path)
    supervisor = CompanionSupervisor(config=cfg)

    reply = supervisor.process_user_input("stop listening")
    assert supervisor.state.is_muted is True
    assert "muted" in reply.lower()


def test_supervisor_voice_command_wasting_time(tmp_path: Path):
    """Verify non-judgmental response to 'am I wasting time?'."""
    cfg = CompanionConfig(storage_directory=tmp_path)
    supervisor = CompanionSupervisor(config=cfg)
    supervisor.state.current_activity = ActivityCategory.WATCHING_VIDEOS

    reply = supervisor.process_user_input("Am I wasting time?")
    assert "Harshan" in reply
    assert "watching_videos" in reply.lower() or "planned break" in reply.lower()


# =============================================================================
# 7. SCREEN OBSERVER & PRIVACY TESTS
# =============================================================================

def test_screen_observer_sensitivity_filter():
    """Verify sensitive apps and tokens are recognized and suppressed."""
    cfg = ScreenObservationConfig(
        enabled=True,
        excluded_apps=["bitwarden", "private", "bank", "token"],
    )
    obs = ScreenObservationEngine(cfg)

    assert obs.is_sensitive("Bitwarden - Password Manager", "bitwarden.exe") is True
    assert obs.is_sensitive("Private Browsing - Firefox", "firefox.exe") is True
    assert obs.is_sensitive("Chase Online Banking", "chrome.exe") is True
    assert obs.is_sensitive("VS Code - main.py", "code.exe") is False


def test_screen_observer_window_categorization():
    """Verify window application categorization heuristics."""
    obs = ScreenObservationEngine()

    assert obs.categorize_window("main.py - Visual Studio Code", "code.exe") == "code_editor"
    assert obs.categorize_window("Windows PowerShell", "powershell.exe") == "terminal"
    assert obs.categorize_window("Google Chrome", "chrome.exe") == "browser"
    assert obs.categorize_window("Notes.txt - Notepad", "notepad.exe") == "document"
    assert obs.categorize_window("Slack", "slack.exe") == "communication"


# =============================================================================
# 8. CLI COMMAND SUITE TESTS
# =============================================================================

def test_cli_companion_status():
    """Verify electorn companion status displays Harshan and bedtime."""
    result = runner.invoke(companion_app, ["status"])
    assert result.exit_code == 0
    assert "Electorn Companion Status" in result.output
    assert "Harshan" in result.output


def test_cli_companion_unified_callback_status():
    """Verify unified single command electorn companion --status works seamlessly."""
    result = runner.invoke(companion_app, ["--status"])
    assert result.exit_code == 0
    assert "Electorn Companion Status" in result.output


def test_companion_interface_in_session_commands(tmp_path: Path):
    """Verify all companion controls work inside the unified interactive session."""
    cfg = CompanionConfig(storage_directory=tmp_path)
    supervisor = CompanionSupervisor(config=cfg)
    ui = CompanionInterface(supervisor=supervisor)

    assert ui._handle_text_input("/status") is True
    assert ui._handle_text_input("/help") is True
    assert ui._handle_text_input("/snap") is True
    assert ui._handle_text_input("/tamil") is True
    assert supervisor.config.personality.code_switch_tamil is False
    assert ui._handle_text_input("/proactive off") is True
    assert supervisor.config.proactive.enabled is False
    assert ui._handle_text_input("/proactive on") is True
    assert supervisor.config.proactive.enabled is True
    assert ui._handle_text_input("/bedtime 22:45") is True
    assert supervisor.config.bedtime.bedtime == "22:45"
    assert ui._handle_text_input("/memory add color=blue") is True
    assert ui._handle_text_input("/memory list") is True
    assert ui._handle_text_input("/focus") is True
    assert supervisor.state.active_mode == CompanionMode.FOCUS


def test_cli_companion_modes():
    """Verify switching to study, night, and privacy modes via CLI."""
    res_study = runner.invoke(companion_app, ["mode", "study"])
    assert res_study.exit_code == 0
    assert "STUDY" in res_study.output

    res_night = runner.invoke(companion_app, ["mode", "night"])
    assert res_night.exit_code == 0
    assert "NIGHT" in res_night.output

    res_priv = runner.invoke(companion_app, ["privacy"])
    assert res_priv.exit_code == 0
    assert "Privacy Mode" in res_priv.output

    # Restore companion
    runner.invoke(companion_app, ["mode", "companion"])


def test_cli_bedtime_and_quiet_hours():
    """Verify bedtime and quiet hours CLI commands."""
    res_bed = runner.invoke(companion_app, ["bedtime", "set", "23:45"])
    assert res_bed.exit_code == 0
    assert "23:45" in res_bed.output

    res_quiet = runner.invoke(companion_app, ["quiet-hours", "set", "23:00", "07:00"])
    assert res_quiet.exit_code == 0
    assert "23:00 to 07:00" in res_quiet.output


def test_cli_voice_and_proactive_toggles():
    """Verify voice and proactive on/off toggles."""
    res_v_off = runner.invoke(companion_app, ["voice", "off"])
    assert res_v_off.exit_code == 0
    res_v_on = runner.invoke(companion_app, ["voice", "on"])
    assert res_v_on.exit_code == 0

    res_p_off = runner.invoke(companion_app, ["proactive", "off"])
    assert res_p_off.exit_code == 0
    res_p_on = runner.invoke(companion_app, ["proactive", "on"])
    assert res_p_on.exit_code == 0


def test_cli_screen_commands():
    """Verify screen enable, disable, and exclusions commands."""
    res_en = runner.invoke(companion_app, ["screen", "enable"])
    assert res_en.exit_code == 0
    assert "ENABLED" in res_en.output

    res_dis = runner.invoke(companion_app, ["screen", "disable"])
    assert res_dis.exit_code == 0
    assert "DISABLED" in res_dis.output

    res_ex = runner.invoke(companion_app, ["screen", "exclusions"])
    assert res_ex.exit_code == 0
    assert "bitwarden" in res_ex.output


def test_cli_screen_live_and_snapshot():
    """Verify screen live and snapshot commands run cleanly."""
    res_live = runner.invoke(companion_app, ["screen", "live", "--count", "1", "--interval", "1"])
    assert res_live.exit_code == 0
    assert "Live Screen Frame #1" in res_live.output

    res_snap = runner.invoke(companion_app, ["screen", "snapshot", "--no-save"])
    assert res_snap.exit_code == 0
    assert "Instant Screen Snapshot & Analysis" in res_snap.output


def test_cli_startup_status():
    """Verify electorn companion startup status command."""
    res = runner.invoke(companion_app, ["startup", "status"])
    assert res.exit_code == 0
    assert "Windows Automatic Login Startup" in res.output


def test_memory_crud_operations(tmp_path: Path):
    """Verify persistent memory CRUD operations and file isolation."""
    mem_engine = MemoryEngine(storage_dir=tmp_path)

    item = mem_engine.add_memory(
        category=MemoryCategory.USER_PREFERENCE,
        key="theme",
        value="Monokai Dark",
    )
    assert item.memory_id.startswith("mem-")
    assert item.key == "theme"

    all_items = mem_engine.load_all()
    assert len(all_items) == 1
    assert all_items[0].value == "Monokai Dark"

    deleted = mem_engine.delete_memory(item.memory_id)
    assert deleted is True
    assert len(mem_engine.load_all()) == 0


def test_companion_tools_command_security():
    """Verify destructive shell commands are blocked."""
    tools = CompanionTools()
    res = tools.run_command("rm -rf /")
    assert res["success"] is False
    assert "destructive" in res["output"].lower()

