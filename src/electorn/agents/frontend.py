"""Frontend Development Specialist Agent."""

from __future__ import annotations

from electorn.agents.base import BaseAgent
from electorn.runtime.model_selector import ModelProfile
from electorn.runtime.ollama_client import OllamaClient


class FrontendAgent(BaseAgent):
    """Builds interactive UI components, templates, client logic, and styling."""

    def __init__(self, client: OllamaClient, model_profile: ModelProfile):
        super().__init__(
            name="Frontend Developer",
            role="Client Interface & Application Specialist",
            icon="💻",
            system_prompt=(
                "You are an expert Frontend Developer. You write responsive HTML/CSS/JavaScript, React/Vue components, "
                "or modern web interfaces. Ensure interactive state management, error states, and responsive styling. "
                "Always provide complete files without placeholders."
            ),
            client=client,
            model_profile=model_profile,
        )
