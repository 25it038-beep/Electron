"""Central supervisor orchestrating Companion Mode state, perception, voice, and tools."""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Callable, Dict, List, Optional

from electorn.companion.memory import MemoryEngine
from electorn.companion.personality import PersonalityEngine
from electorn.companion.proactive_scheduler import ProactiveScheduler
from electorn.companion.schema import (
    CompanionConfig,
    CompanionMode,
    CompanionState,
    ProactiveEvent,
    ScreenObservationReport,
)
from electorn.companion.screen_observer import ScreenObservationEngine
from electorn.companion.storage import CompanionStorage
from electorn.companion.tools import CompanionTools
from electorn.companion.vision_analyzer import VisionAnalyzer
from electorn.companion.voice_session import CompanionVoiceSession
from electorn.providers.local_llm import OllamaLocalProvider

logger = logging.getLogger(__name__)


class CompanionSupervisor:
    """Master controller managing Companion Mode lifecycle, background observation, and conversational intelligence."""

    def __init__(
        self,
        config: Optional[CompanionConfig] = None,
        llm_provider: Optional[OllamaLocalProvider] = None,
    ) -> None:
        self.storage = CompanionStorage()
        self.config = config or self.storage.load_config()
        self.state = CompanionState(active_mode=self.config.mode)

        # Core Subsystems
        self.personality = PersonalityEngine(self.config.personality)
        self.memory = MemoryEngine(self.config.storage_directory)
        self.screen_observer = ScreenObservationEngine(self.config.screen)
        self.vision_analyzer = VisionAnalyzer(self.config.screen)
        self.scheduler = ProactiveScheduler(self.config, self.state)
        self.tools = CompanionTools()
        self.voice = CompanionVoiceSession(
            language=self.config.personality.language,
            voice_gender=self.config.personality.voice_gender,
            speech_speed=self.config.personality.speaking_speed,
            barge_in_enabled=self.config.barge_in_enabled,
        )
        self.llm = llm_provider or OllamaLocalProvider(auto_start=True)

        # Background threads and sync
        self._running = False
        self._obs_thread: Optional[threading.Thread] = None
        self._sched_thread: Optional[threading.Thread] = None
        self.latest_report: Optional[ScreenObservationReport] = None
        self.on_message_cb: Optional[Callable[[str, str], None]] = None
        self.on_state_change_cb: Optional[Callable[[CompanionState], None]] = None

    # =========================================================================
    # LIFECYCLE & MODE MANAGEMENT
    # =========================================================================

    def start(self) -> None:
        """Initialize and start background loops and companion greeting."""
        if self._running:
            return

        self._running = True
        self.state.session_start_time = time.time()
        self.state.is_paused = False

        # Apply mode constraints
        self._apply_mode_rules(self.state.active_mode)

        # Start background threads
        self._obs_thread = threading.Thread(target=self._screen_observation_loop, daemon=True)
        self._obs_thread.start()

        self._sched_thread = threading.Thread(target=self._proactive_scheduler_loop, daemon=True)
        self._sched_thread.start()

        # Log session start
        self.storage.log_activity("session_start", {"mode": self.state.active_mode.value})

    def stop(self) -> None:
        """Shut down background threads and release audio resources."""
        self._running = False
        self.voice.interrupt_speech()
        self.storage.log_activity("session_stop", {"mode": self.state.active_mode.value})

    def pause(self) -> None:
        """Temporarily pause all audio output and proactive interruptions."""
        self.state.is_paused = True
        self.voice.interrupt_speech()
        self.storage.log_activity("session_paused", {})
        self._notify_state_change()

    def resume(self) -> None:
        """Resume active companion services."""
        self.state.is_paused = False
        self.storage.log_activity("session_resumed", {})
        self._notify_state_change()

    def set_mode(self, mode: CompanionMode) -> None:
        """Switch operating mode and adjust subsystem permissions accordingly."""
        self.state.active_mode = mode
        self.config.mode = mode
        self.storage.save_config(self.config)
        self._apply_mode_rules(mode)
        self.storage.log_activity("mode_change", {"new_mode": mode.value})
        self._notify_state_change()

    def _apply_mode_rules(self, mode: CompanionMode) -> None:
        """Enforce strict hardware and perception rules based on active mode."""
        if mode == CompanionMode.PRIVACY:
            self.state.mic_active = False
            self.state.screen_active = False
            self.screen_observer.config.enabled = False
            self.voice.interrupt_speech()
        elif mode == CompanionMode.PASSIVE:
            self.state.mic_active = self.config.voice_enabled
            self.state.screen_active = False
            self.screen_observer.config.enabled = False
        elif mode == CompanionMode.FOCUS:
            self.state.mic_active = self.config.voice_enabled
            self.state.screen_active = self.config.screen.enabled
            self.screen_observer.config.enabled = self.config.screen.enabled
        elif mode in (CompanionMode.COMPANION, CompanionMode.WORK_ASSISTANT):
            self.state.mic_active = self.config.voice_enabled
            self.state.screen_active = self.config.screen.enabled
            self.screen_observer.config.enabled = self.config.screen.enabled

    def _notify_state_change(self) -> None:
        if self.on_state_change_cb:
            try:
                self.on_state_change_cb(self.state)
            except Exception:
                pass

    # =========================================================================
    # BACKGROUND LOOPS
    # =========================================================================

    def _screen_observation_loop(self) -> None:
        """Periodically captures active window context if authorized."""
        while self._running:
            try:
                interval = max(5, self.config.screen.interval_seconds)
                time.sleep(interval)

                if self.state.is_paused or not self.screen_observer.config.enabled:
                    continue

                if self.state.active_mode in (CompanionMode.PRIVACY, CompanionMode.PASSIVE):
                    continue

                img, report = self.screen_observer.capture_screen()
                self.state.active_window_title = report.window_title

                if img is not None:
                    # Run vision analyzer
                    analyzed_report = self.vision_analyzer.analyze(img, report)
                    self.latest_report = analyzed_report

                    # Check for proactive error alert
                    evt = self.scheduler.check_observation_event(analyzed_report)
                    if evt:
                        self._handle_proactive_event(evt)
            except Exception as e:
                logger.debug("Error in screen observation loop: %s", e)

    def _proactive_scheduler_loop(self) -> None:
        """Periodically checks time-based milestones and idle check-ins."""
        while self._running:
            try:
                time.sleep(15)
                if self.state.is_paused or self.state.active_mode in (CompanionMode.PRIVACY, CompanionMode.PASSIVE):
                    continue

                evt = self.scheduler.check_time_based_events()
                if evt:
                    self._handle_proactive_event(evt)
            except Exception as e:
                logger.debug("Error in proactive scheduler loop: %s", e)

    def _handle_proactive_event(self, evt: ProactiveEvent) -> None:
        """Formulate speech and deliver proactive event if conditions permit."""
        speech = self.personality.formulate_proactive_speech(evt)
        evt.delivered = True
        evt.delivered_timestamp = time.time()
        self.scheduler.record_speech_delivered()

        self.storage.log_activity("proactive_speech", {
            "event_type": evt.event_type,
            "title": evt.title,
            "speech": speech,
        })

        if self.on_message_cb:
            self.on_message_cb(self.config.personality.name, speech)

        if self.config.voice_enabled and self.state.active_mode != CompanionMode.PRIVACY:
            self.voice.speak_async(speech)

    # =========================================================================
    # CONVERSATIONAL TURN PROCESSING
    # =========================================================================

    def process_user_input(self, text: str) -> str:
        """Process user query, extract memory, consult tools/screen, and reply."""
        clean_text = text.strip()
        if not clean_text:
            return ""

        self.state.last_user_speech_time = time.time()

        # Check for mode switch voice commands
        lower = clean_text.lower()
        if any(w in lower for w in ("focus mode", "switch to focus", "enter focus")):
            self.set_mode(CompanionMode.FOCUS)
            reply = f"Switching to Focus Mode, {self.config.personality.preferred_address}. I'll stay quiet and keep distractions away."
            self._dispatch_reply(reply)
            return reply

        if any(w in lower for w in ("companion mode", "switch to companion", "girlfriend mode")):
            self.set_mode(CompanionMode.COMPANION)
            reply = f"Companion Mode activated, {self.config.personality.preferred_address}! I'm right here with you."
            self._dispatch_reply(reply)
            return reply

        if any(w in lower for w in ("privacy mode", "switch to privacy", "disable mic")):
            self.set_mode(CompanionMode.PRIVACY)
            reply = "Privacy Mode active. Microphone and screen observation have been turned off completely."
            self._dispatch_reply(reply)
            return reply

        if any(w in lower for w in ("work assistant mode", "assistant mode")):
            self.set_mode(CompanionMode.WORK_ASSISTANT)
            reply = f"Work Assistant mode engaged, {self.config.personality.preferred_address}. Ready to inspect code and run tests."
            self._dispatch_reply(reply)
            return reply

        # Check for tool intent
        tool_reply = self._handle_direct_tool_intent(clean_text)
        if tool_reply:
            self._dispatch_reply(tool_reply)
            return tool_reply

        # Auto-extract and persist preferences
        if self.config.memory_enabled:
            self.memory.extract_and_remember(clean_text)

        # Retrieve relevant memories and screen context
        memories = self.memory.get_prompt_context(limit=6) if self.config.memory_enabled else []
        screen_ctx = ""
        if self.latest_report and not self.latest_report.is_excluded:
            screen_ctx = f"Active window: {self.latest_report.window_title} ({self.latest_report.app_category}). {self.latest_report.visible_summary}"
            if self.latest_report.visible_error:
                screen_ctx += f" Noticeable error: {self.latest_report.visible_error}"

        # Construct system prompt
        sys_prompt = self.personality.build_system_prompt(
            current_mode=self.state.active_mode,
            context_memories=memories,
            screen_context=screen_ctx or None,
        )

        # Call local LLM provider
        raw_reply = self.llm.ask(prompt=clean_text, system_prompt=sys_prompt)
        clean_reply = self.personality.sanitize_llm_response(raw_reply)

        if not clean_reply:
            clean_reply = f"I'm right here with you, {self.config.personality.preferred_address}."

        self._dispatch_reply(clean_reply)
        return clean_reply

    def _handle_direct_tool_intent(self, text: str) -> Optional[str]:
        """Detect and execute direct companion tool commands."""
        lower = text.lower()
        pref = self.config.personality.preferred_address

        # Run tests
        if any(w in lower for w in ("run tests", "run pytest", "run the test suite", "test the project")):
            res = self.tools.run_tests()
            status = "All tests passed successfully!" if res["success"] else "Some tests failed da."
            return f"{pref}, I ran the tests for you. {status}\n{res['output'][:200]}"

        # Search web
        if lower.startswith("search web") or lower.startswith("google ") or "search online for" in lower:
            query = text.replace("search web", "").replace("google", "").replace("search online for", "").strip()
            if query:
                web_res = self.tools.search_web(query)
                return f"{pref}, here is what I found on the web for '{query}':\n{web_res}"

        # List tasks
        if any(w in lower for w in ("what are my tasks", "list tasks", "my todo list")):
            tasks = self.tools.list_tasks()
            if not tasks:
                return f"You don't have any pending tasks right now, {pref}! Relax or tell me what to add."
            items = ", ".join(t["title"] for t in tasks[:4])
            return f"{pref}, here are your pending tasks: {items}."

        return None

    def _dispatch_reply(self, reply: str) -> None:
        """Emit reply to UI callback and voice playback."""
        self.state.last_companion_speech_time = time.time()
        self.storage.log_activity("companion_reply", {"reply": reply})

        if self.on_message_cb:
            self.on_message_cb(self.config.personality.name, reply)

        if self.config.voice_enabled and self.state.active_mode != CompanionMode.PRIVACY:
            self.voice.speak_async(reply)
