"""Ollama API client with streaming, json formatting, and resilience."""

from __future__ import annotations

import json
import re
from typing import Any, Generator, Optional
import httpx
from pydantic import BaseModel, Field


class OllamaModelInfo(BaseModel):
    """Information about an installed Ollama model."""

    name: str
    size_bytes: int = 0
    modified_at: Optional[str] = None
    digest: Optional[str] = None
    format: Optional[str] = None
    family: Optional[str] = None
    parameter_size: Optional[str] = None
    quantization_level: Optional[str] = None


class OllamaResponse(BaseModel):
    """Response wrapper for Ollama generation."""

    content: str
    model: str
    total_duration_ms: Optional[float] = None
    eval_count: Optional[int] = None
    eval_duration_ms: Optional[float] = None
    raw_response: Optional[dict[str, Any]] = None

    def parse_json(self) -> dict[str, Any]:
        """Safely extract JSON object or array from the response content.
        
        Handles markdown codeblocks and extra conversational text from small models.
        """
        text = self.content.strip()
        # 1. Direct parse attempt
        try:
            return json.loads(text)
        except Exception:
            pass

        # 2. Markdown block extraction (```json ... ``` or ``` ...)
        code_block = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
        if code_block:
            candidate = code_block.group(1).strip()
            try:
                return json.loads(candidate)
            except Exception:
                pass

        # 3. First bracket / brace extraction
        brace_match = re.search(r"(\{[\s\S]*\})", text)
        if brace_match:
            try:
                return json.loads(brace_match.group(1).strip())
            except Exception:
                pass

        bracket_match = re.search(r"(\[[\s\S]*\])", text)
        if bracket_match:
            try:
                return json.loads(bracket_match.group(1).strip())
            except Exception:
                pass

        raise ValueError(f"Could not parse valid JSON from Ollama response:\n{text[:500]}...")


class OllamaClient:
    """Client for local Ollama HTTP REST API."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        timeout: float = 180.0,
        mock_mode: bool = False,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.mock_mode = mock_mode
        self._http = httpx.Client(base_url=self.base_url, timeout=self.timeout)

    def is_available(self) -> bool:
        """Check if the Ollama daemon is reachable and responding."""
        if self.mock_mode:
            return True
        try:
            res = self._http.get("/api/tags", timeout=3.0)
            return res.status_code == 200
        except Exception:
            return False

    def list_models(self) -> list[OllamaModelInfo]:
        """List all locally available models installed in Ollama."""
        if self.mock_mode:
            return [
                OllamaModelInfo(name="llama3.2:latest", size_bytes=2_000_000_000, parameter_size="3B"),
                OllamaModelInfo(name="qwen3-vl:4b-instruct", size_bytes=3_300_000_000, parameter_size="4B"),
            ]

        try:
            res = self._http.get("/api/tags")
            res.raise_for_status()
            data = res.json()
            models: list[OllamaModelInfo] = []
            for item in data.get("models", []):
                details = item.get("details", {})
                models.append(
                    OllamaModelInfo(
                        name=item.get("name", ""),
                        size_bytes=item.get("size", 0),
                        modified_at=item.get("modified_at"),
                        digest=item.get("digest"),
                        format=details.get("format"),
                        family=details.get("family"),
                        parameter_size=details.get("parameter_size"),
                        quantization_level=details.get("quantization_level"),
                    )
                )
            return models
        except httpx.ConnectError as err:
            raise ConnectionError(
                f"Cannot connect to Ollama at {self.base_url}. Ensure Ollama is running (`ollama serve`)."
            ) from err
        except Exception as err:
            raise RuntimeError(f"Failed to fetch models from Ollama: {err}") from err

    def chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        temperature: float = 0.2,
        context_tokens: int = 8192,
        format_json: bool = False,
        keep_alive: str = "5m",
    ) -> OllamaResponse:
        """Send chat messages to Ollama and return the full response."""
        if self.mock_mode:
            # Deterministic mock response for testing
            return OllamaResponse(
                content="""{
  "summary": "Mock output generated successfully",
  "files": [
    {
      "path": "app.py",
      "content": "print('Mock application initialized')\\n",
      "action": "create"
    }
  ]
}""",
                model=model,
            )

        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_ctx": context_tokens,
            },
            "keep_alive": keep_alive,
        }
        if format_json:
            payload["format"] = "json"

        try:
            res = self._http.post("/api/chat", json=payload, timeout=self.timeout)
            res.raise_for_status()
            data = res.json()
            content = data.get("message", {}).get("content", "")
            return OllamaResponse(
                content=content,
                model=data.get("model", model),
                total_duration_ms=data.get("total_duration", 0) / 1_000_000,
                eval_count=data.get("eval_count"),
                eval_duration_ms=data.get("eval_duration", 0) / 1_000_000,
                raw_response=data,
            )
        except httpx.ConnectError as err:
            raise ConnectionError(
                f"Lost connection to Ollama at {self.base_url}. Check if Ollama crashed or shut down."
            ) from err
        except Exception as err:
            raise RuntimeError(f"Ollama generation failed: {err}") from err

    def generate(
        self,
        model: str,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.2,
        context_tokens: int = 8192,
        format_json: bool = False,
        keep_alive: str = "5m",
    ) -> OllamaResponse:
        """Generate response via /api/generate endpoint."""
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        return self.chat(
            model=model,
            messages=messages,
            temperature=temperature,
            context_tokens=context_tokens,
            format_json=format_json,
            keep_alive=keep_alive,
        )

    def stream_chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        temperature: float = 0.2,
        context_tokens: int = 8192,
    ) -> Generator[str, None, None]:
        """Stream chat tokens progressively from Ollama."""
        if self.mock_mode:
            yield "Mock streaming response chunk 1\n"
            yield "Mock streaming response chunk 2\n"
            return

        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": temperature,
                "num_ctx": context_tokens,
            },
        }

        with self._http.stream("POST", "/api/chat", json=payload, timeout=self.timeout) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if not line:
                    continue
                try:
                    chunk = json.loads(line)
                    delta = chunk.get("message", {}).get("content", "")
                    if delta:
                        yield delta
                except Exception:
                    continue

    def close(self) -> None:
        """Close HTTP client connection."""
        self._http.close()
