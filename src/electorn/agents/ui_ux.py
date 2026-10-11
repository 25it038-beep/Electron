"""UI/UX Design and Design System Agent."""

from __future__ import annotations

from electorn.agents.base import BaseAgent
from electorn.runtime.model_selector import ModelProfile
from electorn.runtime.ollama_client import OllamaClient


class UIUXAgent(BaseAgent):
    """Designs interfaces, color palettes, CSS variables, and layout contracts."""

    def __init__(self, client: OllamaClient, model_profile: ModelProfile):
        super().__init__(
            name="UI/UX Designer",
            role="Interface & Design System Specialist",
            icon="🎨",
            system_prompt=(
                "You are an expert UI/UX Designer. You craft beautiful, accessible, modern design systems, "
                "CSS variables, Tailwind configurations, component hierarchies, and clean user experience flows. "
                "Ensure responsive layouts, typography scales, and high contrast aesthetics."
            ),
            client=client,
            model_profile=model_profile,
        )
