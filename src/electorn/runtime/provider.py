"""Unified AI Provider Abstraction for Electorn.

Supports Local mode (Ollama), Cloud mode (OpenAI/Anthropic compatible or API keys),
and Automatic mode (graceful fallback and offline detection).
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import Any, Generator, Optional
from pydantic import BaseModel
import httpx

from electorn.runtime.ollama_client import OllamaClient, OllamaResponse
from electorn.storage.config import Config


class ProviderResponse(BaseModel):
    """Normalized response from any AI provider."""

    content: str
    model: str
    provider_name: str
    raw_response: Optional[dict[str, Any]] = None

    def parse_json(self) -> dict[str, Any]:
        """Extract structured JSON if returned."""
        import json
        import re

        text = self.content.strip()
        # Direct parse
        try:
            return json.loads(text)
        except Exception:
            pass

        # Markdown block
        pattern = r"```(?:json)?\s*([\s\S]*?)\s*```"
        match = re.search(pattern, text)
        if match:
            try:
                return json.loads(match.group(1).strip())
            except Exception:
                pass

        # Braces extraction
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except Exception:
                pass

        raise ValueError(f"Could not parse valid JSON from provider response: {text[:200]}")


class BaseProvider(ABC):
    """Abstract foundational AI provider interface."""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.2,
        format_json: bool = False,
    ) -> ProviderResponse:
        """Generate a complete text response."""
        ...

    @abstractmethod
    def stream_chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.2,
    ) -> Generator[str, None, None]:
        """Stream response tokens progressively."""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider backend is reachable and configured."""
        ...

    @abstractmethod
    def get_model_name(self) -> str:
        """Return the active model name."""
        ...


class OllamaProvider(BaseProvider):
    """Local inference provider backed by Ollama."""

    def __init__(self, client: OllamaClient, model_name: str, context_tokens: int = 8192):
        self.client = client
        self.model_name = model_name
        self.context_tokens = context_tokens

    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.2,
        format_json: bool = False,
    ) -> ProviderResponse:
        resp = self.client.generate(
            model=self.model_name,
            prompt=prompt,
            system=system,
            temperature=temperature,
            context_tokens=self.context_tokens,
            format_json=format_json,
        )
        return ProviderResponse(
            content=resp.content,
            model=resp.model,
            provider_name="ollama (local)",
            raw_response=resp.raw_response,
        )

    def stream_chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.2,
    ) -> Generator[str, None, None]:
        return self.client.stream_chat(
            model=self.model_name,
            messages=messages,
            temperature=temperature,
            context_tokens=self.context_tokens,
        )

    def is_available(self) -> bool:
        return self.client.is_available()

    def get_model_name(self) -> str:
        return self.model_name


class CloudProvider(BaseProvider):
    """Cloud AI provider supporting OpenAI/Anthropic-compatible REST endpoints."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.openai.com/v1",
        model_name: str = "gpt-4o-mini",
        timeout: float = 45.0,
    ):
        if api_key is not None:
            self.api_key = api_key
        else:
            self.api_key = os.environ.get("ELECTORN_API_KEY") or os.environ.get("OPENAI_API_KEY") or ""
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name
        self.timeout = timeout

    def is_available(self) -> bool:
        return bool(self.api_key and len(self.api_key.strip()) > 5)

    def get_model_name(self) -> str:
        return self.model_name

    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.2,
        format_json: bool = False,
    ) -> ProviderResponse:
        if not self.is_available():
            raise ConnectionError(
                "Cloud provider is not configured. Set ELECTORN_API_KEY or OPENAI_API_KEY environment variable."
            )

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload: dict[str, Any] = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature,
        }
        if format_json:
            payload["response_format"] = {"type": "json_object"}

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                res = client.post(f"{self.base_url}/chat/completions", json=payload, headers=headers)
                res.raise_for_status()
                data = res.json()
                content = data["choices"][0]["message"]["content"]
                return ProviderResponse(
                    content=content,
                    model=self.model_name,
                    provider_name="cloud",
                    raw_response=data,
                )
        except Exception as err:
            raise RuntimeError(f"Cloud provider request failed: {err}") from err

    def stream_chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.2,
    ) -> Generator[str, None, None]:
        if not self.is_available():
            raise ConnectionError("Cloud provider not configured. Missing API key.")

        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        import json

        with httpx.Client(timeout=self.timeout) as client:
            with client.stream("POST", f"{self.base_url}/chat/completions", json=payload, headers=headers) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    data_str = line[6:].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        delta = chunk["choices"][0]["delta"].get("content", "")
                        if delta:
                            yield delta
                    except Exception:
                        continue


class AutoProvider(BaseProvider):
    """Auto-detects environment: prefers local Ollama if available offline, or cloud if configured."""

    def __init__(self, local_provider: OllamaProvider, cloud_provider: CloudProvider):
        self.local = local_provider
        self.cloud = cloud_provider

    def _resolve_active(self) -> BaseProvider:
        if self.local.is_available():
            return self.local
        if self.cloud.is_available():
            return self.cloud
        return self.local

    def is_available(self) -> bool:
        return self.local.is_available() or self.cloud.is_available()

    def get_model_name(self) -> str:
        return self._resolve_active().get_model_name()

    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.2,
        format_json: bool = False,
    ) -> ProviderResponse:
        active = self._resolve_active()
        return active.generate(prompt, system=system, temperature=temperature, format_json=format_json)

    def stream_chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.2,
    ) -> Generator[str, None, None]:
        active = self._resolve_active()
        return active.stream_chat(messages, temperature=temperature)
