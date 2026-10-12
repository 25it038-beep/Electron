"""Base interface for LLM planning providers in Electorn AI."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional


class BaseLLMProvider(ABC):
    """Abstract interface for task planning models."""

    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider connection is reachable."""
        pass

    @abstractmethod
    def plan_task(self, prompt: str, available_tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Convert a user objective into an ordered list of structured action dicts."""
        pass

    @abstractmethod
    def ask(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """General conversational prompt completion."""
        pass
