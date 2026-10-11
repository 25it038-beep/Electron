"""API Integration and Systems Glue Specialist Agent."""

from __future__ import annotations

from electorn.agents.base import BaseAgent
from electorn.runtime.model_selector import ModelProfile
from electorn.runtime.ollama_client import OllamaClient


class IntegrationAgent(BaseAgent):
    """Integrates frontend with backend, manages environment variables, and third-party APIs."""

    def __init__(self, client: OllamaClient, model_profile: ModelProfile):
        super().__init__(
            name="Integration Specialist",
            role="API & System Integration Engineer",
            icon="🔌",
            system_prompt=(
                "You are an API Integration Engineer. You ensure seamless communication between client and server, "
                "proper configuration loading via environment variables or .env files, error response contracts, "
                "CORS settings, and external SDK integrations."
            ),
            client=client,
            model_profile=model_profile,
        )
