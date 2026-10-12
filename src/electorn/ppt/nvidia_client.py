"""Dedicated, isolated NVIDIA Cloud API Client for PowerPoint Generation.

Exclusively used by the PowerPoint presentation engine. Does not interfere with
or modify the global Ollama integration or general Electorn runtimes.
"""

from __future__ import annotations

import json
import os
import re
import time
from typing import Any, Dict, List, Optional
import httpx


class NvidiaApiError(Exception):
    """Base exception for NVIDIA Cloud API errors."""
    pass


class NvidiaAuthenticationError(NvidiaApiError):
    """Raised when the NVIDIA API key is missing or invalid."""
    pass


class NvidiaRateLimitError(NvidiaApiError):
    """Raised when API rate limits are exceeded."""
    pass


class NvidiaModelNotFoundError(NvidiaApiError):
    """Raised when the specified model identifier is not available."""
    pass


class NvidiaCloudClient:
    """Client for NVIDIA NIM Cloud API (https://integrate.api.nvidia.com/v1).
    
    Provides robust retry with exponential backoff, timeout handling,
    and safe credential retrieval. Secrets are never logged or exposed.
    """

    DEFAULT_BASE_URL = "https://integrate.api.nvidia.com/v1"
    DEFAULT_TIMEOUT = 45.0
    MAX_RETRIES = 3

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> None:
        self.api_key = (
            api_key
            or os.environ.get("NVIDIA_API_KEY")
            or os.environ.get("ELECTORN_NVIDIA_API_KEY")
        )
        self.base_url = (base_url or os.environ.get("NVIDIA_BASE_URL") or self.DEFAULT_BASE_URL).rstrip("/")
        self.timeout = timeout or self.DEFAULT_TIMEOUT

    @property
    def is_configured(self) -> bool:
        """Check whether an API key is present."""
        return bool(self.api_key and self.api_key.strip())

    def is_available(self) -> bool:
        """Check if the client has credentials and can connect."""
        if not self.is_configured:
            return False
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            with httpx.Client(timeout=8.0) as client:
                resp = client.get(f"{self.base_url}/models", headers=headers)
                return resp.status_code == 200
        except Exception:
            return False

    def list_available_models(self) -> List[str]:
        """Fetch verified active model IDs from the NVIDIA NIM catalog."""
        if not self.is_configured:
            raise NvidiaAuthenticationError("NVIDIA API key not configured. Set NVIDIA_API_KEY environment variable.")

        headers = {"Authorization": f"Bearer {self.api_key}"}
        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.get(f"{self.base_url}/models", headers=headers)
                if resp.status_code == 401 or resp.status_code == 403:
                    raise NvidiaAuthenticationError("Invalid or unauthorized NVIDIA API key.")
                resp.raise_for_status()
                data = resp.json().get("data", [])
                return [m["id"] for m in data if "id" in m]
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            raise NvidiaApiError(f"Network error contacting NVIDIA Cloud API: {e}")

    def chat_completion(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 4096,
        format_json: bool = False,
    ) -> str:
        """Execute chat completion with retries, backoff, and reasoning extraction."""
        if not self.is_configured:
            raise NvidiaAuthenticationError(
                "NVIDIA API key is not configured. Please set the NVIDIA_API_KEY environment variable."
            )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        last_error = None
        for attempt in range(self.MAX_RETRIES):
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    resp = client.post(
                        f"{self.base_url}/chat/completions",
                        headers=headers,
                        json=payload,
                    )

                if resp.status_code == 200:
                    data = resp.json()
                    choices = data.get("choices", [])
                    if not choices:
                        return ""
                    message = choices[0].get("message", {})
                    content = message.get("content")
                    # For reasoning models that output to reasoning_content
                    if not content and message.get("reasoning_content"):
                        content = message.get("reasoning_content")
                    
                    raw_text = content or ""
                    if format_json:
                        return self._extract_json_block(raw_text)
                    return raw_text.strip()

                if resp.status_code in (401, 403):
                    raise NvidiaAuthenticationError("NVIDIA API authentication failed. Check your NVIDIA_API_KEY.")

                if resp.status_code == 404:
                    raise NvidiaModelNotFoundError(
                        f"Model '{model}' was not found or is inactive on the NVIDIA API endpoint."
                    )

                if resp.status_code == 429:
                    wait_time = (2 ** attempt) * 2.0
                    time.sleep(wait_time)
                    continue

                if resp.status_code >= 500:
                    wait_time = (2 ** attempt) * 1.5
                    time.sleep(wait_time)
                    continue

                resp.raise_for_status()

            except (httpx.ConnectError, httpx.TimeoutException) as e:
                last_error = e
                time.sleep((2 ** attempt) * 1.5)
            except (NvidiaAuthenticationError, NvidiaModelNotFoundError):
                raise
            except Exception as e:
                last_error = e

        raise NvidiaApiError(f"NVIDIA API request failed after {self.MAX_RETRIES} retries: {last_error}")

    @staticmethod
    def _extract_json_block(text: str) -> str:
        """Extract clean JSON string from LLM response, stripping markdown fences."""
        text = text.strip()
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        # Find first '{' or '[' and last '}' or ']'
        start_obj = text.find("{")
        end_obj = text.rfind("}")
        if start_obj != -1 and end_obj != -1 and end_obj > start_obj:
            return text[start_obj : end_obj + 1].strip()
        return text
