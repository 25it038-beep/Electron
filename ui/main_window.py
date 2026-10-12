"""Main Desktop GUI Window for Electorn AI Voice Automation Engine."""

from __future__ import annotations

import logging
import sys
import threading
import time
from typing import Optional

from PyQt6.QtCore import QObject, QTimer, Qt, pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from agent.action_schema import ExecutionResult, TaskPlan, TaskStep
from agent.executor import TaskExecutor
from agent.planner import TaskPlanner
from agent.task_manager import TaskManager
from agent.task_state import TaskLifecycleState
from agent.tool_registry import ToolRegistry
from config.permissions import PermissionLevel, PermissionManager
from config.settings import AppSettings
from providers.local_llm import OllamaLocalProvider
from providers.ollama_manager import OllamaManager
from storage.database import TaskDatabase
from ui.activity_panel import ActivityPanel
from ui.history_dialog import HistoryDialog
from ui.settings_dialog import SettingsDialog
from ui.styles.dark_theme import DARK_THEME_QSS
from ui.task_timeline import TaskTimeline
from ui.voice_panel import VoicePanel
from voice.microphone import MicrophoneManager
from voice.speech_to_text import SpeechToTextEngine
from voice.text_to_speech import TextToSpeechEngine

logger = logging.getLogger(__name__)


class BridgeSignals(QObject):
    """Thread-safe signals bridging background worker threads with PyQt6 GUI widgets."""
    plan_created = pyqtSignal(object)
    step_updated = pyqtSignal(object)
    task_finished = pyqtSignal(object)
    log_event = pyqtSignal(str, str)
    speech_detected = pyqtSignal(str)
    state_changed = pyqtSignal(object)


class MainWindow(QMainWindow):
    """Main window for Electorn AI desktop application."""

    def __init__(self, settings: Optional[AppSettings] = None) -> None:
        super().__init__()
        self.settings = settings or AppSettings.load()
        self.db = TaskDatabase()
        self.permissions = PermissionManager(self.settings.security)

        # Core Engines
        self.tool_registry = ToolRegistry()
        self.tts = TextToSpeechEngine(
            voice=self.settings.voice.tts_voice,
            rate=self.settings.voice.tts_rate,
        )
        self.stt = SpeechToTextEngine()
        self.mic = MicrophoneManager()

        # Neural Engine: Ollama Local Provider (with auto-detect, auto-start, model check)
        self.ollama_provider = OllamaLocalProvider(
            model_name=self.settings.ai.ollama_model or "llama3.2:1b",
            auto_start=True,
        )

        # Agent Orchestration
        self.signals = BridgeSignals()
        self.planner = TaskPlanner(
            llm_provider=self.ollama_provider,
            permission_engine=self.permissions,
        )
        self.executor = TaskExecutor(
            tool_registry=self.tool_registry,
            permission_engine=self.permissions,
            database=self.db,
            confirm_callback=self._handle_permission_confirm,
        )
        self.task_manager = TaskManager(
            planner=self.planner,
            executor=self.executor,
            tts=self.tts,
        )

        # Connect TaskManager callbacks to Bridge Signals
        self.task_manager.on_plan_created = lambda p: self.signals.plan_created.emit(p)
        self.task_manager.on_step_update = lambda s: self.signals.step_updated.emit(s)
        self.task_manager.on_task_finished = lambda r: self.signals.task_finished.emit(r)
        self.task_manager.on_state_change = lambda st: self.signals.state_changed.emit(st)

        # Continuous voice listener thread flag
        self.voice_listening_active = False
        self._voice_thread: Optional[threading.Thread] = None

        self._init_ui()
        self._wire_signals()

    def _init_ui(self) -> None:
        self.setWindowTitle("⚡ Electorn AI — Complete Voice Automation Engine")
        self.resize(1180, 780)
        self.setStyleSheet(DARK_THEME_QSS)

        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # Top Bar: App Title, Mode Badges, Settings, History
        top_bar = QHBoxLayout()
        title_label = QLabel("⚡ ELECTORN AI")
        title_label.setObjectName("titleLabel")
        top_bar.addWidget(title_label)

        sub_label = QLabel("Windows OS & Web Browser Automation")
        sub_label.setObjectName("mutedLabel")
        top_bar.addWidget(sub_label)

        top_bar.addStretch()

        self.history_btn = QPushButton("📋 History")
        self.history_btn.clicked.connect(self._open_history)
        top_bar.addWidget(self.history_btn)

        self.settings_btn = QPushButton("⚙ Settings")
        self.settings_btn.clicked.connect(self._open_settings)
        top_bar.addWidget(self.settings_btn)

        main_layout.addLayout(top_bar)

        # Voice Input Panel
        self.voice_panel = VoicePanel(self)
        main_layout.addWidget(self.voice_panel)

        # Center split: Left = Timeline, Right = Activity Log
        splitter = QSplitter(Qt.Orientation.Horizontal)

        self.timeline = TaskTimeline(self)
        splitter.addWidget(self.timeline)

        self.activity_panel = ActivityPanel(self)
        splitter.addWidget(self.activity_panel)

        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        main_layout.addWidget(splitter, 1)

        # Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Engine initialized: Ready • Voice: en-US-AvaNeural (Female) • Mode: Safe")

    def _wire_signals(self) -> None:
        # Voice panel signals
        self.voice_panel.voice_command_submitted.connect(self._on_command_received)
        self.voice_panel.voice_interrupted.connect(self._on_stop_requested)
        self.voice_panel.listening_toggled.connect(self._on_listening_toggled)

        # Thread signals to UI updates
        self.signals.plan_created.connect(self._on_plan_created)
        self.signals.step_updated.connect(self._on_step_updated)
        self.signals.task_finished.connect(self._on_task_finished)
        self.signals.speech_detected.connect(self.voice_panel.set_transcription)
        self.signals.state_changed.connect(self._on_state_changed)

    def _on_command_received(self, command: str) -> None:
        self.activity_panel.log(f"Received instruction: \"{command}\"", "INFO")
        self.task_manager.submit_command(command, async_exec=True)

    def _on_stop_requested(self) -> None:
        self.task_manager.cancel_current_task()
        self.activity_panel.log("Execution interrupted by user.", "WARN")
        self.status_bar.showMessage("Task cancelled.")

    def _on_plan_created(self, plan: TaskPlan) -> None:
        self.timeline.load_plan(plan)
        self.activity_panel.log(f"Plan constructed with {len(plan.steps)} steps.", "INFO")
        self.status_bar.showMessage(f"Executing: {plan.objective}")

    def _on_step_updated(self, step: TaskStep) -> None:
        self.timeline.update_step(step)
        if step.status == "completed":
            self.activity_panel.log(f"Step '{step.action}' verified successfully: {step.verification_evidence}", "SUCCESS")
        elif step.status == "failed":
            self.activity_panel.log(f"Step '{step.action}' failed: {step.error}", "ERROR")

    def _on_task_finished(self, result: ExecutionResult) -> None:
        if result.success:
            self.activity_panel.log(f"Workflow finished: {result.message}", "SUCCESS")
            self.status_bar.showMessage(f"Task completed successfully in {result.duration_sec:.1f}s")
        else:
            self.activity_panel.log(f"Workflow ended with failure: {result.message}", "ERROR")
            self.status_bar.showMessage("Task execution failed.")

    def _on_state_changed(self, state: TaskLifecycleState) -> None:
        self.status_bar.showMessage(f"State: {state.value.upper()}")

    def _on_listening_toggled(self, active: bool) -> None:
        self.voice_listening_active = active
        if active and (self._voice_thread is None or not self._voice_thread.is_alive()):
            self._voice_thread = threading.Thread(target=self._continuous_voice_loop, daemon=True)
            self._voice_thread.start()

    def _continuous_voice_loop(self) -> None:
        """Background listening loop recognizing spoken commands."""
        self.activity_panel.log("Continuous microphone listener active.", "INFO")
        while self.voice_listening_active:
            try:
                # Capture short audio snippet
                audio_bytes, _ = self.mic.record_chunk(duration_sec=3.5)
                if not self.voice_listening_active:
                    break
                if audio_bytes:
                    text = self.stt.recognize(audio_bytes)
                    if text:
                        self.signals.speech_detected.emit(text)
                        self._on_command_received(text)
                        time.sleep(1.0)
            except Exception as e:
                time.sleep(1.0)

    def _handle_permission_confirm(self, step: TaskStep) -> bool:
        """Prompt user with PyQt6 dialog for Level 2 confirmation."""
        self.activity_panel.log(f"Confirmation requested for: {step.action}", "WARN")
        msg = (
            f"Electorn AI requests approval to execute:\n\n"
            f"Action: {step.action}\n"
            f"Description: {step.description}\n"
            f"Parameters: {step.parameters}\n\n"
            f"Do you permit this action to execute?"
        )
        reply = QMessageBox.question(
            self,
            "Security Confirmation Required",
            msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        approved = (reply == QMessageBox.StandardButton.Yes)
        if approved:
            self.activity_panel.log(f"Action '{step.action}' confirmed by user.", "INFO")
        else:
            self.activity_panel.log(f"Action '{step.action}' rejected by user.", "WARN")
        return approved

    def _open_settings(self) -> None:
        dlg = SettingsDialog(self.settings, self)
        dlg.exec()

    def _open_history(self) -> None:
        dlg = HistoryDialog(self.db, self)
        dlg.exec()

    def closeEvent(self, event) -> None:
        self.voice_listening_active = False
        self.task_manager.cancel_current_task()
        self.tool_registry.browser_engine.close()
        event.accept()
