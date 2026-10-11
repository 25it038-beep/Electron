"""DevOps and Environment Setup Specialist Agent."""

from __future__ import annotations

from electorn.agents.base import BaseAgent
from electorn.runtime.model_selector import ModelProfile
from electorn.runtime.ollama_client import OllamaClient


class DevOpsAgent(BaseAgent):
    """Generates package manifests, run scripts, Dockerfiles, and README docs."""

    def __init__(self, client: OllamaClient, model_profile: ModelProfile):
        super().__init__(
            name="DevOps Engineer",
            role="Environment & Deployment Specialist",
            icon="🚀",
            system_prompt=(
                "You are a DevOps & Environment Setup Engineer. You configure project dependency files "
                "(requirements.txt, package.json, pyproject.toml, Dockerfile), environment variables (.env.example), "
                "and helpful README.md documentation with precise start and test instructions."
            ),
            client=client,
            model_profile=model_profile,
        )
