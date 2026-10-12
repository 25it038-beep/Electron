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

    def start_service(self, max_wait_sec: int = 20) -> bool:
        """Start Ollama background server daemon if not already running."""
        if self.is_running():
            logger.info("Ollama service is already active and responding.")
            return True

        exe = self.find_executable() or "ollama"
        logger.info(f"Starting Ollama daemon in background using: {exe} serve")

        # Spawn headless persistent background process
        try:
            if os.name == "nt":
                DETACHED = getattr(subprocess, "DETACHED_PROCESS", 0x00000008)
                CREATE_NEW_GROUP = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200)
                flags = DETACHED | CREATE_NEW_GROUP
                
                # Attempt 1: Direct detached subprocess via shell
                subprocess.Popen(
                    f'"{exe}" serve',
                    shell=True,
                    creationflags=flags,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    stdin=subprocess.DEVNULL,
                )
            else:
                subprocess.Popen(
                    [exe, "serve"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    stdin=subprocess.DEVNULL,
                    start_new_session=True,
                )
        except Exception as e:
            logger.warning(f"Standard spawn failed: {e}. Trying PowerShell Start-Process fallback...")
            try:
                if os.name == "nt":
                    subprocess.Popen(
                        ["powershell", "-WindowStyle", "Hidden", "-Command", "Start-Process", f'"{exe}"', "-ArgumentList", "serve", "-WindowStyle", "Hidden"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        stdin=subprocess.DEVNULL,
                    )
            except Exception as ps_err:
                logger.error(f"PowerShell fallback failed: {ps_err}")

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

    def install_ollama(self, timeout_sec: int = 300) -> bool:
        """Automatically install Ollama if not present on the PC."""
        logger.info("Ollama is not installed. Initiating automated installation...")

        # Strategy 1: Windows Package Manager (winget)
        if shutil.which("winget"):
            try:
                logger.info("Attempting automated installation via Windows Package Manager (winget)...")
                proc = subprocess.run(
                    [
                        "winget", "install", "--id", "Ollama.Ollama",
                        "-e", "--silent", "--accept-source-agreements", "--accept-package-agreements"
                    ],
                    capture_output=True,
                    text=True,
                    timeout=timeout_sec,
                )
                if proc.returncode == 0:
                    logger.info("winget successfully installed Ollama.")
                    time.sleep(3.0)
                    if self.find_executable():
                        return True
            except Exception as w_err:
                logger.warning(f"winget installation encountered: {w_err}")

        # Strategy 2: Direct Official Windows Installer Download & Silent Execution
        try:
            logger.info("Downloading official Ollama Windows installer from https://ollama.com/download/OllamaSetup.exe...")
            installer_url = "https://ollama.com/download/OllamaSetup.exe"
            temp_dir = os.environ.get("TEMP", os.path.expanduser("~"))
            installer_path = os.path.join(temp_dir, "OllamaSetup.exe")

            # Download executable installer
            urllib.request.urlretrieve(installer_url, installer_path)
            if os.path.exists(installer_path) and os.path.getsize(installer_path) > 1024 * 1024:
                logger.info("Running Ollama installer silently...")
                run_proc = subprocess.run(
                    [installer_path, "/DIR=" + os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Ollama")],
                    capture_output=True,
                    timeout=timeout_sec,
                )
                time.sleep(4.0)
                if self.find_executable():
                    logger.info("Ollama executable discovered following direct installation.")
                    return True
        except Exception as d_err:
            logger.error(f"Direct download/install failed: {d_err}")

        # Strategy 3: Linux / macOS automatic curl script
        if os.name != "nt":
            try:
                logger.info("Running curl -fsSL https://ollama.com/install.sh | sh...")
                proc = subprocess.run(
                    ["sh", "-c", "curl -fsSL https://ollama.com/install.sh | sh"],
                    capture_output=True,
                    timeout=timeout_sec,
                )
                if proc.returncode == 0:
                    return True
            except Exception as u_err:
                logger.error(f"Unix installation error: {u_err}")

        return self.is_installed()

    def ensure_ready(self, target_model: Optional[str] = None) -> dict[str, Any]:
        """Ensure Ollama is installed, running, and has the specified model ready.
        
        If Ollama is missing, automatically installs it.
        If the daemon is inactive, automatically launches it.
        If the model is missing, automatically pulls it.
        
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

        # 1. Verify installation, or auto-install if missing on this PC
        if not self.is_installed():
            logger.info("Ollama not found on this computer. Beginning automatic zero-touch installation...")
            installed = self.install_ollama()
            if not installed:
                return {
                    "installed": False,
                    "running": False,
                    "model_ready": False,
                    "active_model": model,
                    "message": (
                        "Ollama was not found and automatic installation could not be completed. "
                        "Please install Ollama manually from https://ollama.com/download."
                    ),
                }

        # 2. Ensure running
        if not self.is_running():
            logger.info("Ollama is installed but daemon is not active. Launching automatically...")
            started = self.start_service(max_wait_sec=20)
            if not started:
                return {
                    "installed": True,
                    "running": False,
                    "model_ready": False,
                    "active_model": model,
                    "message": "Failed to auto-start Ollama server daemon.",
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
