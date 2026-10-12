"""OpenAI-compatible HTTP API LLM provider."""

from __future__ import annotations

import json
import urllib.request
from typing import Any, Optional

from providers.base import BaseLLMProvider


class APILLMProvider(BaseLLMProvider):
    """Integrates with OpenAI-compatible chat completion endpoints."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.openai.com/v1",
        model_name: str = "gpt-4o-mini",
        timeout: int = 25,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name
        self.timeout = timeout

    def is_available(self) -> bool:
        """Check if API key is provided."""
        return bool(self.api_key and self.api_key.strip())

    def ask(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Execute chat completion request."""
        if not self.is_available():
            return "API LLM provider is not configured with an API key."

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": 0.2,
        }

        try:
            req = urllib.request.Request(
                f"{self.base_url}/chat/completions",
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                },
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["choices"][0]["message"]["content"].strip()
        except Exception as err:
            return f"API LLM Error: {err}"

    def plan_task(self, prompt: str, available_tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Generate structured task plan via API."""
        tools_summary = "\n".join([f"- {t['name']}: {t['description']}" for t in available_tools])
        system = (
            "You are the Electorn AI task planner. Output ONLY a valid JSON array of structured actions.\n"
            f"Available tools:\n{tools_summary}\n\n"
            "Format: [{\"action\": \"tool_name\", \"parameters\": {\"param\": \"value\"}}]\n"
            "Output pure JSON only."
        )

        resp = self.ask(prompt, system_prompt=system)
        try:
            clean = resp.strip()
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
