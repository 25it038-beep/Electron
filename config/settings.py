"""Application settings and configuration persistence for Electorn AI."""

from __future__ import annotations

import json
import os
import pathlib
from dataclasses import asdict, dataclass, field
from typing import Optional


@dataclass
class VoiceSettings:
    """Voice recognition and synthesis settings."""
    mic_device_index: Optional[int] = None
    sample_rate: int = 16000
    speech_speed: int = 1
    voice_gender: str = "female"
    neural_model: str = "en-US-AvaNeural"
    continuous_mode: bool = True
    push_to_talk: bool = False
    wake_word: str = "hey electorn"
    wake_word_enabled: bool = False
    spoken_confirmations: bool = True
    input_language: str = "en-US"


@dataclass
class BrowserSettings:
    """Selenium browser automation settings."""
    browser_type: str = "edge"  # "edge" or "chrome"
    headless: bool = False
    download_dir: str = str(pathlib.Path.home() / "Downloads")
    page_load_timeout_sec: int = 25
    implicit_wait_sec: int = 5
    reuse_session: bool = True


@dataclass
class AISettings:
    """AI reasoning and planning provider settings."""
    provider: str = "local_ollama"  # "local_ollama", "api_llm", "deterministic"
    model_name: str = "llama3.2"
    ollama_base_url: str = "http://localhost:11434"
    api_key: Optional[str] = None
    api_base_url: Optional[str] = None
    temperature: float = 0.2
    max_tokens: int = 2048


@dataclass
class SecuritySettings:
    """Security and safety settings."""
    strict_permissions: bool = True
    auto_approve_level_1: bool = True
    require_confirm_level_2: bool = True
    block_level_3: bool = True
    allowed_directories: list[str] = field(default_factory=lambda: [
        str(pathlib.Path.home() / "Desktop"),
        str(pathlib.Path.home() / "Documents"),
        str(pathlib.Path.home() / "Downloads"),
        str(pathlib.Path.cwd()),
    ])


@dataclass
class AppSettings:
    """Root application configuration."""
    voice: VoiceSettings = field(default_factory=VoiceSettings)
    browser: BrowserSettings = field(default_factory=BrowserSettings)
    ai: AISettings = field(default_factory=AISettings)
    security: SecuritySettings = field(default_factory=SecuritySettings)
    db_path: str = str(pathlib.Path.home() / ".electorn" / "electorn_tasks.db")
    app_dir: str = str(pathlib.Path.home() / ".electorn")


def get_default_config_path() -> pathlib.Path:
    """Return default configuration path in user directory."""
    dir_path = pathlib.Path.home() / ".electorn"
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path / "settings.json"


def load_settings(config_path: Optional[pathlib.Path] = None) -> AppSettings:
    """Load settings from JSON file or return defaults."""
    target_path = config_path or get_default_config_path()
    if not target_path.exists():
        settings = AppSettings()
        save_settings(settings, target_path)
        return settings

    try:
        data = json.loads(target_path.read_text(encoding="utf-8"))
        voice_data = data.get("voice", {})
        browser_data = data.get("browser", {})
        ai_data = data.get("ai", {})
        sec_data = data.get("security", {})

        return AppSettings(
            voice=VoiceSettings(**voice_data),
            browser=BrowserSettings(**browser_data),
            ai=AISettings(**ai_data),
            security=SecuritySettings(**sec_data),
            db_path=data.get("db_path", str(pathlib.Path.home() / ".electorn" / "electorn_tasks.db")),
            app_dir=data.get("app_dir", str(pathlib.Path.home() / ".electorn")),
        )
    except Exception:
        return AppSettings()


def save_settings(settings: AppSettings, config_path: Optional[pathlib.Path] = None) -> None:
    """Save settings dataclass to JSON file."""
    target_path = config_path or get_default_config_path()
    target_path.parent.mkdir(parents=True, exist_ok=True)
    data = asdict(settings)
    target_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
