"""Ollama local model provider implementation."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Optional

from providers.base import BaseLLMProvider
from providers.ollama_manager import OllamaManager


class OllamaLocalProvider(BaseLLMProvider):
    """Integrates with local Ollama service with automatic daemon startup and model verification."""

    def __init__(self, base_url: str = "http://localhost:11434", model_name: str = "llama3.2:1b", timeout: int = 20, auto_start: bool = True) -> None:
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name
        self.timeout = timeout
        self.manager = OllamaManager(base_url=self.base_url, preferred_model=self.model_name)
        if auto_start:
            self._ensure_online()

    def _ensure_online(self) -> None:
        """Auto-start server and verify model readiness."""
        res = self.manager.ensure_ready(self.model_name)
        if res.get("active_model"):
            self.model_name = res["active_model"]

    def is_available(self) -> bool:
        """Check if Ollama server is responding."""
        try:
            req = urllib.request.Request(f"{self.base_url}/api/tags")
            with urllib.request.urlopen(req, timeout=3) as resp:
                return resp.status == 200
        except Exception:
            return False

    def ask(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Query Ollama generate endpoint."""
        payload: dict[str, Any] = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
        }
        if system_prompt:
            payload["system"] = system_prompt

        try:
            req = urllib.request.Request(
                f"{self.base_url}/api/generate",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("response", "").strip()
        except Exception as err:
            return f"Ollama connection error: {err}"

    def plan_task(self, prompt: str, available_tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Generate structured JSON action plan using Ollama."""
        tools_summary = "\n".join([f"- {t['name']}: {t['description']}" for t in available_tools])
        system = (
            "You are the Electorn AI task planner. Analyze the user's voice command and output "
            "ONLY a valid JSON array of structured actions to accomplish the goal.\n"
            f"Available tools:\n{tools_summary}\n\n"
            "Format: [{\"action\": \"tool_name\", \"parameters\": {\"param\": \"value\"}}]\n"
            "Output pure JSON only without markdown formatting."
        )

        response = self.ask(prompt, system_prompt=system)
        try:
            # Strip markdown fences if present
            clean = response.strip()
            if clean.startswith("```"):
                clean = clean.split("\n", 1)[1]
                if clean.endswith("```"):
                    clean = clean.rsplit("```", 1)[0]
            clean = clean.strip()
            parsed = json.loads(clean)
            if isinstance(parsed, list):
                return parsed
        except Exception:
            pass
        return []
