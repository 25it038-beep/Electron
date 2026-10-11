"""QA & Testing Specialist Agent."""

from __future__ import annotations

from electorn.agents.base import BaseAgent
from electorn.runtime.model_selector import ModelProfile
from electorn.runtime.ollama_client import OllamaClient


class QATesterAgent(BaseAgent):
    """Generates automated unit, functional, and integration test suites."""

    def __init__(self, client: OllamaClient, model_profile: ModelProfile):
        super().__init__(
            name="QA Engineer",
            role="Testing & Quality Assurance Specialist",
            icon="🧪",
            system_prompt=(
                "You are a rigorous QA & Test Automation Engineer. You write comprehensive unit and integration "
                "tests using standard frameworks (e.g. pytest, unittest, jest). Test edge cases, validation, "
                "error handling, and happy paths. Make test suites completely self-contained and runnable."
            ),
            client=client,
            model_profile=model_profile,
        )
