"""Backend Engineering Agent."""

from __future__ import annotations

from electorn.agents.base import BaseAgent
from electorn.runtime.model_selector import ModelProfile
from electorn.runtime.ollama_client import OllamaClient


class BackendAgent(BaseAgent):
    """Develops API endpoints, business logic, authentication, and core algorithms."""

    def __init__(self, client: OllamaClient, model_profile: ModelProfile):
        super().__init__(
            name="Backend Developer",
            role="Server & Business Logic Specialist",
            icon="⚙️",
            system_prompt=(
                "You are a Senior Backend Developer. You build robust server architectures, REST/GraphQL endpoints, "
                "services, error handling, validation, and business logic. Write clean, modular, testable code "
                "with explicit typing and complete implementations."
            ),
            client=client,
            model_profile=model_profile,
        )
