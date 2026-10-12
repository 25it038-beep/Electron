"""Voice Control and Audio Visualizer Panel."""

from __future__ import annotations

import math
import random
from PyQt6.QtCore import QPointF, QRectF, QTimer, Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QPainter, QPen
from PyQt6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class AudioVisualizerWidget(QWidget):
    """Dynamic animated glowing waveform visualizer for speech activity."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(64)
        self.is_active = False
        self.energy_level = 0.0
        self.phase = 0.0

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._animate)
        self.timer.start(33)  # ~30 FPS

    def set_active(self, active: bool) -> None:
        self.is_active = active
        self.update()

    def set_energy(self, level: float) -> None:
        self.energy_level = max(0.0, min(1.0, level))
        self.update()

    def _animate(self) -> None:
        if self.is_active:
            self.phase += 0.15
            self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()
        height = self.height()
        mid_y = height / 2.0

        # Background
        painter.fillRect(self.rect(), QColor("#0B0F19"))

        # Base centerline
        pen_dim = QPen(QColor("#1E293B"), 1)
        painter.setPen(pen_dim)
        painter.drawLine(0, int(mid_y), width, int(mid_y))

        num_bars = 48
        bar_width = width / (num_bars * 1.5)

        for i in range(num_bars):
            x = i * (bar_width * 1.5) + (bar_width / 2.0)
            if self.is_active:
                amp = (math.sin(self.phase + i * 0.3) * 0.5 + 0.5) * (height * 0.4) * max(0.2, self.energy_level)
            else:
                amp = 2.0  # Idle faint pulse

            # Glow color
            color = QColor("#06B6D4") if self.is_active else QColor("#334155")
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.PenStyle.NoPen)
            rect = QRectF(x, mid_y - amp, bar_width, amp * 2)
            painter.drawRoundedRect(rect, 2, 2)


class VoicePanel(QFrame):
    """Voice input controls: Push-to-talk, continuous listening, waveform visualizer, and manual input."""

    voice_command_submitted = pyqtSignal(str)
    voice_interrupted = pyqtSignal()
    listening_toggled = pyqtSignal(bool)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("card")
        self.is_listening = False
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        # Header with Voice Mode indicator
        header = QHBoxLayout()
        title = QLabel("Voice & Neural Input")
        title.setObjectName("sectionHeader")
        header.addWidget(title)
        header.addStretch()

        self.continuous_cb = QCheckBox("Continuous Hands-Free Mode")
        self.continuous_cb.setStyleSheet("color: #94A3B8; font-size: 12px;")
        self.continuous_cb.toggled.connect(self._on_continuous_toggled)
        header.addWidget(self.continuous_cb)
        layout.addLayout(header)

        # Waveform Visualizer
        self.visualizer = AudioVisualizerWidget()
        layout.addWidget(self.visualizer)

        # Status and Transcription Feedback
        self.status_lbl = QLabel("Status: Ready • Press Mic or speak 'Hey Electorn'")
        self.status_lbl.setStyleSheet("color: #94A3B8; font-size: 12px;")
        layout.addWidget(self.status_lbl)

        # Controls row: Mic Button + Editable command bar + Send + Stop
        ctrl_layout = QHBoxLayout()
        ctrl_layout.setSpacing(8)

        # Mic Toggle Button
        self.mic_btn = QPushButton("🎤")
        self.mic_btn.setObjectName("micBtn")
        self.mic_btn.setCheckable(True)
        self.mic_btn.clicked.connect(self._toggle_mic)
        ctrl_layout.addWidget(self.mic_btn)

        # Editable Command Line
        self.cmd_input = QLineEdit()
        self.cmd_input.setPlaceholderText("Say something or type an automation command (e.g., 'Open Chrome and extract table to CSV')...")
        self.cmd_input.returnPressed.connect(self._submit_manual)
        ctrl_layout.addWidget(self.cmd_input)

        # Execute Button
        self.exec_btn = QPushButton("Execute")
        self.exec_btn.setObjectName("primaryBtn")
        self.exec_btn.clicked.connect(self._submit_manual)
        ctrl_layout.addWidget(self.exec_btn)

        # Interrupt / Stop Button
        self.stop_btn = QPushButton("⏹ Stop")
        self.stop_btn.setObjectName("dangerBtn")
        self.stop_btn.clicked.connect(self._on_stop_clicked)
        ctrl_layout.addWidget(self.stop_btn)

        layout.addLayout(ctrl_layout)

    def _toggle_mic(self) -> None:
        self.is_listening = self.mic_btn.isChecked()
        self.visualizer.set_active(self.is_listening)
        if self.is_listening:
            self.visualizer.set_energy(0.8)
            self.status_lbl.setText("Status: Listening for speech...")
            self.status_lbl.setStyleSheet("color: #06B6D4; font-weight: bold;")
        else:
            self.visualizer.set_energy(0.0)
            self.status_lbl.setText("Status: Ready")
            self.status_lbl.setStyleSheet("color: #94A3B8;")
        self.listening_toggled.emit(self.is_listening)

    def _on_continuous_toggled(self, checked: bool) -> None:
        if checked:
            self.status_lbl.setText("Status: Continuous listening active (Wake-word: 'Hey Electorn')")
            self.status_lbl.setStyleSheet("color: #10B981; font-weight: bold;")
            self.visualizer.set_active(True)
            self.visualizer.set_energy(0.4)
        else:
            self.status_lbl.setText("Status: Push-to-talk mode active")
            self.status_lbl.setStyleSheet("color: #94A3B8;")
            self.visualizer.set_active(False)
        self.listening_toggled.emit(checked)

    def _submit_manual(self) -> None:
        text = self.cmd_input.text().strip()
        if text:
            self.voice_command_submitted.emit(text)
            self.cmd_input.clear()

    def _on_stop_clicked(self) -> None:
        self.voice_interrupted.emit()
        self.status_lbl.setText("Status: Interrupted by user.")
        self.status_lbl.setStyleSheet("color: #EF4444;")
        self.visualizer.set_active(False)
        self.mic_btn.setChecked(False)

    def set_transcription(self, text: str) -> None:
        """Display live speech transcription in the input box."""
        self.cmd_input.setText(text)
        self.status_lbl.setText(f"Transcribed: \"{text}\"")
        self.status_lbl.setStyleSheet("color: #38BDF8;")
