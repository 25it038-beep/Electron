"""Ollama lifecycle manager: auto-discovery, background startup, model verification, and auto-pulling."""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from typing import Optional

logger = logging.getLogger(__name__)


class OllamaManager:
    """Manages Ollama service lifecycle: installation check, starting background daemon,
    and verifying/pulling required models automatically.
    """

    DEFAULT_BASE_URL = "http://127.0.0.1:11434"
    DEFAULT_MODEL = "llama3.2:1b"  # Fast, lightweight default model for voice automation

    def __init__(self, base_url: str = DEFAULT_BASE_URL, preferred_model: str = DEFAULT_MODEL) -> None:
        self.base_url = base_url.rstrip("/")
        self.preferred_model = preferred_model
        self._executable_path: Optional[str] = None

    def find_executable(self) -> Optional[str]:
        """Find the ollama.exe binary path on Windows."""
        if self._executable_path and os.path.exists(self._executable_path):
            return self._executable_path

        # 1. Check system PATH
        which_path = shutil.which("ollama")
        if which_path:
            self._executable_path = which_path
            return which_path

        # 2. Check standard Windows AppData locations
        user_profile = os.environ.get("USERPROFILE", "")
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        candidates = [
            os.path.join(local_app_data, "Programs", "Ollama", "ollama.exe"),
            os.path.join(user_profile, "AppData", "Local", "Programs", "Ollama", "ollama.exe"),
            r"C:\Program Files\Ollama\ollama.exe",
        ]

        for cand in candidates:
            if os.path.exists(cand):
                self._executable_path = cand
                return cand

        return None

    def is_installed(self) -> bool:
        """Check if Ollama executable is found."""
        return self.find_executable() is not None

    def is_running(self) -> bool:
        """Check if Ollama API server is active and responding."""
        try:
            req = urllib.request.Request(f"{self.base_url}/api/tags")
            with urllib.request.urlopen(req, timeout=2) as resp:
                return resp.status == 200
        except Exception:
            return False

    def start_service(self, max_wait_sec: int = 15) -> bool:
        """Start Ollama background server daemon if not already running."""
        if self.is_running():
            logger.info("Ollama service is already active and responding.")
            return True

        exe = self.find_executable()
        if not exe:
            logger.error("Ollama executable was not found. Cannot start service automatically.")
            return False

        logger.info(f"Starting Ollama daemon in background using: {exe} serve")
        try:
            # Spawn headless background process
            creationflags = 0
            if os.name == "nt":
                # DETACHED_PROCESS or CREATE_NO_WINDOW
                creationflags = subprocess.CREATE_NO_WINDOW

            subprocess.Popen(
                [exe, "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                creationflags=creationflags,
                close_fds=True,
            )
        except Exception as e:
            logger.error(f"Failed to spawn Ollama process: {e}")
            return False

        # Wait until endpoint is responsive
        start_t = time.time()
        while time.time() - start_t < max_wait_sec:
            time.sleep(1.0)
            if self.is_running():
                logger.info("Ollama daemon successfully started and responding to HTTP API.")
                return True

        logger.warning(f"Ollama daemon spawned but did not respond within {max_wait_sec} seconds.")
        return False

    def list_models(self) -> list[str]:
        """Return list of model names installed locally in Ollama."""
        if not self.is_running():
            return []

        try:
            req = urllib.request.Request(f"{self.base_url}/api/tags")
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                models = [m.get("name", "") for m in data.get("models", [])]
                return [m for m in models if m]
        except Exception as e:
            logger.error(f"Error listing Ollama models: {e}")
            return []

    def has_model(self, model_name: str) -> bool:
        """Check if a specific model or model family is installed."""
        models = self.list_models()
        name_lower = model_name.lower()
        for m in models:
            m_lower = m.lower()
            if m_lower == name_lower:
                return True
            # Also match base name (e.g. 'llama3.2:1b' matches 'llama3.2:1b', 'llama3.2:latest')
            if name_lower in m_lower or m_lower.startswith(name_lower):
                return True
        return False

    def pull_model(self, model_name: str, timeout_sec: int = 300) -> bool:
        """Pull a model via the Ollama HTTP API or CLI."""
        logger.info(f"Initiating download/pull of model '{model_name}'...")

        # 1. Try pulling via HTTP API
        try:
            payload = json.dumps({"name": model_name, "stream": False}).encode("utf-8")
            req = urllib.request.Request(
                f"{self.base_url}/api/pull",
                data=payload,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
                if resp.status == 200:
                    logger.info(f"Model '{model_name}' pulled successfully via API.")
                    return True
        except Exception as api_err:
            logger.warning(f"API pull failed ({api_err}), falling back to CLI pull...")

        # 2. Fallback to CLI pull
        exe = self.find_executable()
        if exe:
            try:
                proc = subprocess.run(
                    [exe, "pull", model_name],
                    capture_output=True,
                    text=True,
                    timeout=timeout_sec,
                )
                if proc.returncode == 0:
                    logger.info(f"Model '{model_name}' pulled successfully via CLI.")
                    return True
            except Exception as cli_err:
                logger.error(f"CLI pull error: {cli_err}")

        return False

    def ensure_ready(self, target_model: Optional[str] = None) -> dict[str, Any]:
        """Ensure Ollama is installed, running, and has the specified model ready.
        
        Returns a summary status dictionary:
        {
            "installed": bool,
            "running": bool,
            "model_ready": bool,
            "active_model": str,
            "message": str
        }
        """
        model = target_model or self.preferred_model

        # 1. Verify installation
        if not self.is_installed():
            return {
                "installed": False,
                "running": False,
                "model_ready": False,
                "active_model": model,
                "message": (
                    "Ollama is not installed. Please install Ollama from https://ollama.com/download "
                    "or run 'winget install Ollama.Ollama'."
                ),
            }

        # 2. Ensure running
        if not self.is_running():
            logger.info("Ollama is installed but not running. Launching automatically...")
            started = self.start_service(max_wait_sec=15)
            if not started:
                return {
                    "installed": True,
                    "running": False,
                    "model_ready": False,
                    "active_model": model,
                    "message": "Failed to auto-start Ollama server.",
                }

        # 3. Verify models
        installed_models = self.list_models()
        if not installed_models:
            # No models installed at all, pull preferred
            logger.info(f"No Ollama models found. Automatically pulling '{model}'...")
            pulled = self.pull_model(model)
            if not pulled:
                return {
                    "installed": True,
                    "running": True,
                    "model_ready": False,
                    "active_model": model,
                    "message": f"Ollama is running, but failed to pull model '{model}'.",
                }
            return {
                "installed": True,
                "running": True,
                "model_ready": True,
                "active_model": model,
                "message": f"Ollama is running and model '{model}' was installed and verified.",
            }

        # Check if requested model exists
        if self.has_model(model):
            return {
                "installed": True,
                "running": True,
                "model_ready": True,
                "active_model": model,
                "message": f"Ollama is active and model '{model}' is verified.",
            }

        # If requested model not present, check if any compatible model exists
        usable_model = installed_models[0]
        for m in installed_models:
            if "llama" in m or "qwen" in m:
                usable_model = m
                break

        return {
            "installed": True,
            "running": True,
            "model_ready": True,
            "active_model": usable_model,
            "message": f"Ollama is active with model '{usable_model}' ready for task planning.",
        }
