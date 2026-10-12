"""Application Settings and Configuration Dialog."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QVBoxLayout,
)

from config.settings import AppSettings


class SettingsDialog(QDialog):
    """Configuration dialog for voice models, browser choices, LLM endpoints, and safety policies."""

    def __init__(self, settings: AppSettings, parent=None) -> None:
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle("Electorn AI — Settings & Hardware Engine")
        self.setFixedWidth(520)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Voice Settings
        voice_group = QGroupBox("Voice & Speech Engine")
        v_layout = QFormLayout(voice_group)

        self.voice_name_combo = QComboBox()
        self.voice_name_combo.addItems([
            "en-US-AvaNeural (Female Edge Neural - Recommended)",
            "en-US-JennyNeural (Female Edge Neural)",
            "en-US-GuyNeural (Male Edge Neural)",
            "Microsoft Zira Desktop (SAPI Local Fallback)",
        ])
        v_layout.addRow("TTS Voice:", self.voice_name_combo)

        self.rate_spin = QSpinBox()
        self.rate_spin.setRange(-50, 50)
        self.rate_spin.setValue(0)
        v_layout.addRow("Speech Rate (%):", self.rate_spin)

        self.wake_word_edit = QLineEdit(self.settings.voice.wake_word)
        v_layout.addRow("Wake Word:", self.wake_word_edit)

        layout.addWidget(voice_group)

        # Automation Settings
        auto_group = QGroupBox("Automation Engine")
        a_layout = QFormLayout(auto_group)

        self.browser_combo = QComboBox()
        self.browser_combo.addItems(["edge", "chrome", "firefox"])
        self.browser_combo.setCurrentText(self.settings.browser.default_browser)
        a_layout.addRow("Default Browser:", self.browser_combo)

        self.headless_cb = QCheckBox("Headless Browser (Hidden)")
        self.headless_cb.setChecked(self.settings.browser.headless)
        a_layout.addRow("", self.headless_cb)

        layout.addWidget(auto_group)

        # AI Reasoning Settings
        ai_group = QGroupBox("AI Reasoning Provider")
        ai_layout = QFormLayout(ai_group)

        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["deterministic (Offline Rule Planner)", "ollama (Local LLM)", "api (OpenAI Compatible)"])
        ai_layout.addRow("Planner Engine:", self.provider_combo)

        self.ollama_model_edit = QLineEdit(self.settings.ai.ollama_model)
        ai_layout.addRow("Ollama Model:", self.ollama_model_edit)

        self.api_key_edit = QLineEdit(self.settings.ai.api_key or "")
        self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_edit.setPlaceholderText("Optional API key (sk-...)")
        ai_layout.addRow("API Key:", self.api_key_edit)

        layout.addWidget(ai_group)

        # Buttons
        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btn_box.accepted.connect(self._save_and_accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def _save_and_accept(self) -> None:
        self.settings.voice.wake_word = self.wake_word_edit.text()
        self.settings.browser.default_browser = self.browser_combo.currentText()
        self.settings.browser.headless = self.headless_cb.isChecked()
        self.settings.ai.ollama_model = self.ollama_model_edit.text()
        self.settings.ai.api_key = self.api_key_edit.text()
        self.settings.save()
        self.accept()
