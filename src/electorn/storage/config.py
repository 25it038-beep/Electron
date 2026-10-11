"""Configuration models and file handling for Electorn AI."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field
import yaml


class RuntimeConfig(BaseModel):
    """Runtime and Ollama engine configurations."""

    ollama_base_url: str = Field(
        default="http://localhost:11434",
        description="Base URL for the local Ollama instance",
    )
    model: Optional[str] = Field(
        default=None,
        description="Target Ollama model name (None = auto-select best available)",
    )
    fallback_model: Optional[str] = Field(
        default="llama3.2:latest",
        description="Fallback small model if primary is unavailable",
    )
    timeout_seconds: int = Field(
        default=300,
        description="Request timeout in seconds for Ollama API calls",
    )
    temperature: float = Field(
        default=0.2,
        description="Sampling temperature for code generation",
    )
    context_tokens: int = Field(
        default=8192,
        description="Context window size to request from Ollama",
    )
    keep_alive: str = Field(
        default="5m",
        description="Ollama keep_alive parameter for model unloading/caching",
    )


class OrchestrationConfig(BaseModel):
    """Execution orchestration and memory options."""

    sequential_execution: bool = Field(
        default=True,
        description="Execute agents sequentially to minimize memory and GPU RAM footprint",
    )
    max_repair_attempts: int = Field(
        default=3,
        description="Maximum iterations for automated self-repair loop",
    )
    auto_install_deps: bool = Field(
        default=False,
        description="Automatically install project dependencies without interactive prompt",
    )
    allow_command_execution: bool = Field(
        default=True,
        description="Allow running verified build and test commands",
    )
    verbosity: int = Field(
        default=1,
        description="Verbosity level: 0=minimal, 1=standard rich UI, 2=detailed debug",
    )


class WorkspaceConfig(BaseModel):
    """Workspace path and safety constraints."""

    workspace_dir: str = Field(
        default=".",
        description="Target project directory",
    )
    ignore_patterns: list[str] = Field(
        default_factory=lambda: [
            ".git",
            "__pycache__",
            ".pytest_cache",
            "node_modules",
            ".venv",
            "venv",
            "dist",
            "build",
            ".electorn",
        ],
        description="Directory and file patterns to ignore during file discovery",
    )
    backup_before_edit: bool = Field(
        default=True,
        description="Create backup snapshot before applying modifications",
    )


class Config(BaseModel):
    """Complete Electorn AI configuration schema."""

    runtime: RuntimeConfig = Field(default_factory=RuntimeConfig)
    orchestration: OrchestrationConfig = Field(default_factory=OrchestrationConfig)
    workspace: WorkspaceConfig = Field(default_factory=WorkspaceConfig)


def get_global_config_path() -> Path:
    """Return path to global user configuration (~/.electorn/config.yaml)."""
    home = Path.home()
    return home / ".electorn" / "config.yaml"


def get_local_config_path(workspace_dir: Path | str = ".") -> Path:
    """Return path to project-level configuration (.electorn.yaml)."""
    return Path(workspace_dir) / ".electorn.yaml"


def load_config(workspace_dir: Path | str = ".") -> Config:
    """Load configuration with precedence: Local > Global > Defaults.
    
    Environment variables (e.g. ELECTORN_MODEL, OLLAMA_HOST) also override.
    """
    config_data: dict = {}

    global_path = get_global_config_path()
    if global_path.is_file():
        try:
            with open(global_path, "r", encoding="utf-8") as f:
                loaded = yaml.safe_load(f)
                if isinstance(loaded, dict):
                    config_data.update(loaded)
        except Exception:
            pass

    local_path = get_local_config_path(workspace_dir)
    if local_path.is_file():
        try:
            with open(local_path, "r", encoding="utf-8") as f:
                loaded = yaml.safe_load(f)
                if isinstance(loaded, dict):
                    config_data.update(loaded)
        except Exception:
            pass

    config = Config.model_validate(config_data)

    # Environment variable overrides
    if env_host := os.getenv("OLLAMA_HOST"):
        config.runtime.ollama_base_url = env_host
    if env_base_url := os.getenv("ELECTORN_OLLAMA_URL"):
        config.runtime.ollama_base_url = env_base_url
    if env_model := os.getenv("ELECTORN_MODEL"):
        config.runtime.model = env_model

    return config


def save_config(config: Config, path: Path) -> None:
    """Save configuration model to a YAML file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(config.model_dump(), f, default_flow_style=False, sort_keys=False)
