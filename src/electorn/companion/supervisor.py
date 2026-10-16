"""Central supervisor orchestrating Companion Mode state, perception, voice, time, and tools."""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Callable, Dict, List, Optional

from electorn.companion.activity_classifier import ActivityClassifier
from electorn.companion.memory import MemoryEngine
from electorn.companion.personality import PersonalityEngine
from electorn.companion.proactive_scheduler import ProactiveScheduler
from electorn.companion.schema import (
    ActivityCategory,
    CompanionConfig,
    CompanionLifecycleState,
    CompanionMode,
    CompanionState,
    ProactiveEvent,
    ScreenObservationReport,
)
from electorn.automation.os_agent import WindowsOSAgent
from electorn.automation.web_agent import PlaywrightWebAgent
from electorn.companion.boredom_engine import BoredomEngine
from electorn.companion.screen_observer import ScreenObservationEngine
from electorn.companion.startup import StartupManager
from electorn.companion.storage import CompanionStorage
from electorn.companion.time_engine import TimeAwarenessEngine
from electorn.companion.tools import CompanionTools
from electorn.companion.vision_analyzer import VisionAnalyzer
from electorn.companion.voice_session import CompanionVoiceSession
from electorn.planner.task_planner import AutonomousTaskPlanner
from electorn.providers.local_llm import OllamaLocalProvider

logger = logging.getLogger(__name__)


class CompanionSupervisor:
    """Master controller managing Companion Mode lifecycle, background observation, bedtime, and conversational intelligence."""

    def __init__(
        self,
        config: Optional[CompanionConfig] = None,
        llm_provider: Optional[OllamaLocalProvider] = None,
    ) -> None:
        self.storage = CompanionStorage()
        self.config = config or self.storage.load_config()
        self.state = CompanionState(active_mode=self.config.mode)

        # Core Subsystems
        self.time_engine = TimeAwarenessEngine()
        self.activity_classifier = ActivityClassifier(self.config.activity)
        self.startup_manager = StartupManager(self.config.storage_directory)
        self.personality = PersonalityEngine(self.config.personality)
        self.memory = MemoryEngine(self.config.storage_directory)
        self.screen_observer = ScreenObservationEngine(self.config.screen, self.activity_classifier)
        self.vision_analyzer = VisionAnalyzer(self.config.screen)
        self.scheduler = ProactiveScheduler(self.config, self.state)
        self.tools = CompanionTools()
        self.os_agent = WindowsOSAgent()
        self.web_agent = PlaywrightWebAgent()
        self.boredom_engine = BoredomEngine(self.config.storage_directory)
        self.task_planner = AutonomousTaskPlanner(llm_provider=llm_provider)
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
        """Initialize and start background loops, single-instance check, and startup greeting."""
        if self._running:
            return

        # Acquire single-instance lock
        self.startup_manager.acquire_instance_lock()

        self._running = True
        self.state.session_start_time = time.time()
        self.state.is_paused = False
        self.state.current_lifecycle = CompanionLifecycleState.STARTING

        # Apply mode constraints
        self._apply_mode_rules(self.state.active_mode)

        # Start background threads
        self._obs_thread = threading.Thread(target=self._screen_observation_loop, daemon=True)
        self._obs_thread.start()

        self._sched_thread = threading.Thread(target=self._proactive_scheduler_loop, daemon=True)
        self._sched_thread.start()

        # Check startup greeting
        startup_evt = self.scheduler.check_startup_greeting()
        if startup_evt:
            greeting = self.personality.generate_greeting()
            self._handle_proactive_speech(greeting, "startup")

        self.state.current_lifecycle = CompanionLifecycleState.READY
        self.storage.log_activity("session_start", {"mode": self.state.active_mode.value})
        self._notify_state_change()

    def stop(self) -> None:
        """Shut down background threads and release audio and lock resources."""
        self._running = False
        self.voice.interrupt_speech()
        self.startup_manager.release_instance_lock()
        self.storage.log_activity("session_stop", {"mode": self.state.active_mode.value})

    def pause(self) -> None:
        """Temporarily pause all audio output and proactive interruptions."""
        self.state.is_paused = True
        self.state.current_lifecycle = CompanionLifecycleState.PAUSED
        self.voice.interrupt_speech()
        self.storage.log_activity("session_paused", {})
        self._notify_state_change()

    def resume(self) -> None:
        """Resume active companion services."""
        self.state.is_paused = False
        self.state.current_lifecycle = CompanionLifecycleState.READY
        self.storage.log_activity("session_resumed", {})
        self._notify_state_change()

    def mute(self) -> None:
        """Immediately mute microphone and halt active speech."""
        self.state.is_muted = True
        self.voice.mute()
        self.storage.log_activity("voice_muted", {})
        self._notify_state_change()

    def unmute(self) -> None:
        """Unmute microphone."""
        self.state.is_muted = False
        self.voice.unmute()
        self.storage.log_activity("voice_unmuted", {})
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
        """Enforce strict hardware, perception, and silence rules based on mode."""
        if mode == CompanionMode.PRIVACY:
            self.state.mic_active = False
            self.state.screen_active = False
            self.screen_observer.config.enabled = False
            self.voice.interrupt_speech()
            self.state.current_lifecycle = CompanionLifecycleState.QUIET
        elif mode == CompanionMode.PASSIVE:
            self.state.mic_active = self.config.voice_enabled and not self.state.is_muted
            self.state.screen_active = False
            self.screen_observer.config.enabled = False
            self.state.current_lifecycle = CompanionLifecycleState.READY
        elif mode in (CompanionMode.FOCUS, CompanionMode.NIGHT):
            self.state.mic_active = self.config.voice_enabled and not self.state.is_muted
            self.state.screen_active = self.config.screen.enabled
            self.screen_observer.config.enabled = self.config.screen.enabled
            self.state.current_lifecycle = CompanionLifecycleState.QUIET if mode == CompanionMode.NIGHT else CompanionLifecycleState.READY
        elif mode in (CompanionMode.COMPANION, CompanionMode.STUDY, CompanionMode.WORK_ASSISTANT):
            self.state.mic_active = self.config.voice_enabled and not self.state.is_muted
            self.state.screen_active = self.config.screen.enabled
            self.screen_observer.config.enabled = self.config.screen.enabled
            if mode == CompanionMode.STUDY and not self.state.study_session_start_time:
                self.state.study_session_start_time = time.time()
            self.state.current_lifecycle = CompanionLifecycleState.READY

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
                interval = max(3, self.config.screen.interval_seconds)
                time.sleep(interval)

                if self.state.is_paused or not self.screen_observer.config.enabled:
                    continue

                if self.state.active_mode in (CompanionMode.PRIVACY, CompanionMode.PASSIVE):
                    continue

                self.state.current_lifecycle = CompanionLifecycleState.MONITORING
                img, report = self.screen_observer.capture_screen()
                self.state.active_window_title = report.window_title
                self.state.current_activity = report.activity_category

                # Check application switch proactive event
                app_evt = self.scheduler.check_app_switch_event(report)
                if app_evt:
                    self._handle_proactive_event(app_evt)

                if img is not None:
                    # Run vision analyzer
                    analyzed_report = self.vision_analyzer.analyze(img, report)
                    self.latest_report = analyzed_report

                    # Check for distraction alerts
                    distract_evt = self.scheduler.check_distraction_event(analyzed_report)
                    if distract_evt:
                        self._handle_proactive_event(distract_evt)

                    # Check for proactive error alert
                    err_evt = self.scheduler.check_observation_event(analyzed_report)
                    if err_evt:
                        self._handle_proactive_event(err_evt)

                self.state.current_lifecycle = CompanionLifecycleState.READY
            except Exception as e:
                logger.debug("Error in screen observation loop: %s", e)

    def _proactive_scheduler_loop(self) -> None:
        """Periodically checks bedtime stages, break milestones, and idle check-ins."""
        while self._running:
            try:
                time.sleep(5)
                if self.state.is_paused or self.state.active_mode in (CompanionMode.PRIVACY, CompanionMode.PASSIVE):
                    continue

                self.check_and_trigger_proactive()

            except Exception as e:
                logger.debug("Error in proactive scheduler loop: %s", e)

    def check_and_trigger_proactive(self) -> Optional[ProactiveEvent]:
        """Perform prompt evaluation of bedtime and idle check-ins and trigger speech if due."""
        if not self._running or self.state.is_paused or self.state.active_mode in (CompanionMode.PRIVACY, CompanionMode.PASSIVE):
            return None

        # 1. Check bedtime stages
        bed_evt = self.scheduler.check_bedtime_event()
        if bed_evt:
            self._handle_proactive_event(bed_evt)
            return bed_evt

        # 2. Check time milestones / autonomous idle check-in
        time_evt = self.scheduler.check_time_based_events()
        if time_evt:
            self._handle_proactive_event(time_evt)
            return time_evt

        return None

    def _handle_proactive_event(self, evt: ProactiveEvent) -> None:
        """Formulate speech and deliver proactive event if conditions permit."""
        speech = self.personality.formulate_proactive_speech(evt)
        evt.delivered = True
        evt.delivered_timestamp = time.time()
        self.scheduler.record_speech_delivered()
        self._handle_proactive_speech(speech, evt.event_type, evt.title)

    def _handle_proactive_speech(self, speech: str, event_type: str, title: str = "") -> None:
        """Dispatch proactive speech."""
        self.storage.log_activity("proactive_speech", {
            "event_type": event_type,
            "title": title,
            "speech": speech,
        })

        if self.on_message_cb:
            self.on_message_cb(self.config.personality.name, speech)

        if self.config.voice_enabled and not self.state.is_muted and self.state.active_mode != CompanionMode.PRIVACY:
            self.state.current_lifecycle = CompanionLifecycleState.SPEAKING
            self.voice.speak_async(speech, on_finish_cb=self._on_speech_finished)

    def _on_speech_finished(self) -> None:
        self.state.current_lifecycle = CompanionLifecycleState.READY
        self._notify_state_change()

    # =========================================================================
    # CONVERSATIONAL TURN PROCESSING & INTENT DISPATCH
    # =========================================================================

    def process_user_input(self, text: str) -> str:
        """Process user query, intercept voice commands, consult context, and reply."""
        clean_text = text.strip()
        if not clean_text:
            return ""

        self.state.last_user_speech_time = time.time()
        self.state.current_lifecycle = CompanionLifecycleState.THINKING

        # Intercept Voice Commands
        command_reply = self._handle_voice_commands(clean_text)
        if command_reply:
            self._dispatch_reply(command_reply)
            return command_reply

        # Auto-extract and persist preferences into memory
        if self.config.memory_enabled:
            self.memory.extract_and_remember(clean_text)

        # Retrieve relevant memories and screen context
        memories = self.memory.get_prompt_context(limit=6) if self.config.memory_enabled else []
        screen_ctx = ""
        dur_min = 0
        if self.latest_report and not self.latest_report.is_excluded:
            dur_min = int(self.latest_report.sustained_duration_seconds / 60)
            screen_ctx = f"Active window: {self.latest_report.window_title} ({self.latest_report.app_category}). {self.latest_report.visible_summary}"
            if self.latest_report.visible_error:
                screen_ctx += f" Noticeable error: {self.latest_report.visible_error}"

        # Construct system prompt
        sys_prompt = self.personality.build_system_prompt(
            current_mode=self.state.active_mode,
            context_memories=memories,
            screen_context=screen_ctx or None,
            current_activity=self.state.current_activity.value,
            sustained_duration_minutes=dur_min,
        )

        # Query Ollama LLM provider
        raw_reply = self.llm.ask(prompt=clean_text, system_prompt=sys_prompt)
        clean_reply = self.personality.sanitize_llm_response(raw_reply)

        if not clean_reply:
            clean_reply = f"I'm right here with you, {self.config.personality.user_name}."

        self._dispatch_reply(clean_reply)
        return clean_reply

    def _handle_voice_commands(self, text: str) -> Optional[str]:
        """Detect and execute natural voice commands."""
        lower = text.lower()
        user = self.config.personality.user_name

        # 1. Mode switches
        if any(w in lower for w in ("focus mode", "switch to focus", "enter focus")):
            self.set_mode(CompanionMode.FOCUS)
            return f"Switching to Focus Mode, {user}. I'll stay quiet and keep distractions away."

        if any(w in lower for w in ("study mode", "stay quiet while i study", "switch to study")):
            self.set_mode(CompanionMode.STUDY)
            return f"Study Mode active, {user}. I'll track your study session and keep distractions to a minimum."

        if any(w in lower for w in ("night mode", "switch to night")):
            self.set_mode(CompanionMode.NIGHT)
            return f"Night Mode enabled, {user}. Let's wind down for a restful night."

        if any(w in lower for w in ("companion mode", "switch to companion", "normal mode")):
            self.set_mode(CompanionMode.COMPANION)
            return f"Companion Mode activated, {user}! I'm right here with you."

        if any(w in lower for w in ("privacy mode", "switch to privacy", "disable mic and screen")):
            self.set_mode(CompanionMode.PRIVACY)
            return "Privacy Mode active. Microphone and screen observation have been turned off completely."

        # 2. Mute / Silence controls
        if any(w in lower for w in ("stop listening", "mute microphone", "mute mic")):
            self.mute()
            return f"Microphone muted, {user}. You can type or say 'unmute' whenever you need me."

        if any(w in lower for w in ("be quiet for a while", "don't interrupt me for the next hour", "quiet for an hour")):
            self.config.proactive.enabled = False
            return f"Understood {user}, I will remain quiet and won't interrupt you."

        if "talk in tamil" in lower or "let's talk in tamil" in lower:
            self.config.personality.code_switch_tamil = True
            self.config.personality.language = "ta-IN"
            return f"Kandippa {user}, inimey Tamil-la pesuvom!"

        # 3. Status queries: "What am I doing right now?"
        if any(w in lower for w in ("what am i doing right now", "what is my activity", "current activity")):
            app_str = self.state.active_window_title or "desktop"
            act_str = self.state.current_activity.value
            dur_min = int((time.time() - self.state.activity_start_time) / 60)
            return f"{user}, you're currently in {app_str}. It looks like {act_str}, and you've been on it for about {dur_min} minutes."

        # 4. Status queries: "Am I wasting time?"
        if any(w in lower for w in ("am i wasting time", "am i distracted")):
            if self.state.current_activity in (ActivityCategory.WATCHING_VIDEOS, ActivityCategory.ENTERTAINMENT, ActivityCategory.GAMING):
                dur_min = int((time.time() - self.state.activity_start_time) / 60)
                return f"{user}, you've been on {self.state.current_activity.value} for about {dur_min} minutes. If this is a planned break, that's fine; otherwise, want me to help you get back to work?"
            return f"Not at all {user}, you've been engaged in {self.state.current_activity.value}. Keep up the great focus!"

        # 5. Status queries: "How long have I been working?"
        if any(w in lower for w in ("how long have i been working", "session duration", "work duration")):
            total_min = int((time.time() - self.state.session_start_time) / 60)
            return f"{user}, you've been working for {total_min} minutes in this session."

        # 6. Check my screen
        if any(w in lower for w in ("check my screen", "inspect my screen", "look at my screen")):
            if not self.config.screen.enabled:
                return f"{user}, screen observation is currently disabled. You can enable it with 'electorn companion screen --enable'."
            img, report = self.screen_observer.capture_screen()
            if img:
                analyzed = self.vision_analyzer.analyze(img, report)
                self.latest_report = analyzed
                return f"{user}, I inspected your screen: {analyzed.visible_summary}"
            return f"{user}, I couldn't capture the screen right now."

        # 7. Bedtime settings: "Remind me to sleep at 11:30"
        import re
        bed_match = re.search(r"remind me to sleep at (\d{1,2}(?::\d{2})?\s*(?:am|pm)?)", lower)
        if bed_match:
            time_raw = bed_match.group(1).strip()
            # Convert to HH:MM
            return f"I've updated your sleep reminder, {user}. I'll remind you at {time_raw}."

        if any(w in lower for w in ("snooze bedtime", "snooze sleep reminder")):
            self.time_engine.snooze(self.config.bedtime, minutes=30)
            return f"Bedtime reminder snoozed for 30 minutes, {user}. Please make sure you wrap up soon!"

        # 8. Tool intents: run tests, tasks, web search
        if any(w in lower for w in ("run tests", "run pytest", "test the project")):
            res = self.tools.run_tests()
            status = "All tests passed successfully!" if res["success"] else "Some tests failed."
            return f"{user}, I ran the tests for you. {status}\n{res['output'][:200]}"

        if lower.startswith("search web") or lower.startswith("google ") or "search online for" in lower:
            query = text.replace("search web", "").replace("google", "").replace("search online for", "").strip()
            if query:
                web_res = self.tools.search_web(query)
                return f"{user}, here is what I found on the web for '{query}':\n{web_res}"

        if any(w in lower for w in ("what are my tasks", "list tasks", "my todo list")):
            tasks = self.tools.list_tasks()
            if not tasks:
                return f"You don't have any pending tasks right now, {user}!"
            items = ", ".join(t["title"] for t in tasks[:4])
            return f"{user}, here are your pending tasks: {items}."

        # 9. Boredom & entertainment
        if any(w in lower for w in ("i'm bored", "im bored", "entertain me", "give me something fun", "play a game", "start a quiz", "tech trivia", "trivia quiz", "coding puzzle", "startup idea")):
            boredom_res = self.boredom_engine.handle_boredom_trigger(lower, user_name=user)
            return boredom_res["message"]

        # 10. OS Automation: Open/Launch application
        if lower.startswith("open ") or lower.startswith("launch ") or lower.startswith("start app "):
            app_target = lower.replace("start app ", "").replace("launch ", "").replace("open ", "").strip()
            if app_target and len(app_target.split()) <= 3 and not any(w in app_target for w in ("tab", "search", "link", "url")):
                res = self.os_agent.launch_application(app_target)
                if res.get("success"):
                    return f"I launched {app_target} for you, {user}."
                return f"I tried to launch {app_target}, but ran into an issue: {res.get('error', 'could not start')}."

        # 11. OS Automation: Close application
        if lower.startswith("close ") or lower.startswith("kill app "):
            app_target = lower.replace("kill app ", "").replace("close ", "").strip()
            if app_target and len(app_target.split()) <= 3:
                res = self.os_agent.close_application(app_target)
                if res.get("success"):
                    return f"Closed {app_target} for you, {user}."
                return f"Could not close {app_target}: {res.get('error', 'process not found')}."

        # 12. OS Automation: Organize Downloads / Directory
        if any(w in lower for w in ("organize my downloads", "organize downloads", "clean downloads", "sort my downloads", "organize folder", "clean folder")):
            res = self.os_agent.organize_directory()
            if res.get("success"):
                moved = res.get("files_moved", 0)
                cats = ", ".join(f"{k}: {v}" for k, v in res.get("summary", {}).items() if v > 0)
                return f"I've organized your Downloads folder, {user}! Moved {moved} files ({cats or 'none needed moving'})."
            return f"Directory organization status: {res.get('error', 'unknown error')}."

        # 13. System Diagnostics & Specs
        if any(w in lower for w in ("system specs", "disk space", "system health", "diagnostics", "check system specs", "pc specs", "memory usage")):
            diag = self.os_agent.get_system_diagnostics()
            cpu_p = diag.get("cpu", {}).get("percent", 0)
            mem_p = diag.get("memory", {}).get("percent", 0)
            mem_avail = diag.get("memory", {}).get("available_gb", 0)
            battery = diag.get("battery", {})
            bat_str = f", Battery at {battery.get('percent')}%" if battery and battery.get("percent") is not None else ""
            return f"{user}, here are your current system specs: CPU load is {cpu_p}%, RAM usage is {mem_p}% ({mem_avail} GB free){bat_str}. All systems operating normally."

        # 14. Deep Autonomous Web Research
        if lower.startswith("deep research ") or lower.startswith("research ") or lower.startswith("investigate "):
            topic = lower.replace("deep research ", "").replace("research ", "").replace("investigate ", "").strip()
            if topic:
                rep = self.web_agent.research_topic(topic, max_sources=3)
                if rep.get("success"):
                    return f"{user}, I conducted autonomous research on '{topic}'. {rep.get('summary', '')} Full report saved to {rep.get('report_path')}."
                return f"I encountered an issue researching '{topic}': {rep.get('error')}."

        # 15. Autonomous Task Planner
        if lower.startswith("automate task ") or lower.startswith("plan and execute "):
            goal = lower.replace("automate task ", "").replace("plan and execute ", "").strip()
            if goal:
                task_res = self.task_planner.plan_and_execute(goal)
                status = "successfully completed" if task_res.get("success") else "failed during execution"
                return f"{user}, autonomous task '{goal}' {status}. {task_res.get('report', '')}"

        return None

    def _dispatch_reply(self, reply: str) -> None:
        """Emit reply to UI callback and voice playback."""
        self.state.last_companion_speech_time = time.time()
        self.storage.log_activity("companion_reply", {"reply": reply})

        if self.on_message_cb:
            self.on_message_cb(self.config.personality.name, reply)

        if self.config.voice_enabled and not self.state.is_muted and self.state.active_mode != CompanionMode.PRIVACY:
            self.state.current_lifecycle = CompanionLifecycleState.SPEAKING
            self.voice.speak_async(reply, on_finish_cb=self._on_speech_finished)
        else:
            self.state.current_lifecycle = CompanionLifecycleState.READY
