"""Database & Data Engineering Specialist Agent."""

from __future__ import annotations

from electorn.agents.base import BaseAgent
from electorn.runtime.model_selector import ModelProfile
from electorn.runtime.ollama_client import OllamaClient


class DatabaseAgent(BaseAgent):
    """Designs schemas, ORMs, tables, indexes, and database migrations."""

    def __init__(self, client: OllamaClient, model_profile: ModelProfile):
        super().__init__(
            name="Database Engineer",
            role="Data Modeling & Storage Specialist",
            icon="🗄️",
            system_prompt=(
                "You are an experienced Database Engineer. You design clean data models (e.g. SQLite, SQLAlchemy, "
                "Pydantic schemas, PostgreSQL), indexes, migration scripts, and seed data generators. "
                "Ensure referential integrity, strong typing, and efficient querying."
            ),
            client=client,
            model_profile=model_profile,
        )
