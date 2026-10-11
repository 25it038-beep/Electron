"""Lead System Architect and Product Strategy Agent."""

from __future__ import annotations

import json
from electorn.agents.base import BaseAgent
from electorn.runtime.model_selector import ModelProfile
from electorn.runtime.ollama_client import OllamaClient
from electorn.workspace.project_state import FileEntry, ProjectSpecification


class ArchitectAgent(BaseAgent):
    """Analyzes specifications, creates technical blueprints, and designs file manifests."""

    def __init__(self, client: OllamaClient, model_profile: ModelProfile):
        super().__init__(
            name="Architect",
            role="Lead System Architect",
            icon="🧠",
            system_prompt=(
                "You are the Lead Software Architect. Your job is to analyze the user's project requirements "
                "and design a robust, clean, lightweight system specification. Choose appropriate modern stacks "
                "(e.g., FastAPI/Flask/SQLite for Python, Vite/React for modern web, or pure modular Python for tools). "
                "Plan explicit file structures with purpose and components."
            ),
            client=client,
            model_profile=model_profile,
        )

    def design_system(self, user_prompt: str) -> ProjectSpecification:
        """Create a full ProjectSpecification from the user prompt."""
        prompt = f"""
USER REQUEST:
"{user_prompt}"

TASK:
Design the complete application architecture.
Return a single JSON object with the exact following schema:
{{
  "project_name": "kebab-case-project-name",
  "tagline": "Short one-sentence summary",
  "overview": "Detailed overview of the application architecture",
  "tech_stack": {{
    "language": "Python",
    "framework": "FastAPI",
    "database": "SQLite",
    "testing": "pytest"
  }},
  "key_features": ["Feature 1", "Feature 2", "Feature 3"],
  "dependencies": ["fastapi", "uvicorn", "pydantic"],
  "dev_dependencies": ["pytest", "httpx"],
  "run_command": "python main.py",
  "test_command": "pytest",
  "file_manifest": [
    {{"path": "models.py", "purpose": "Data models and schemas", "component": "database", "language": "python"}},
    {{"path": "services.py", "purpose": "Core business logic", "component": "backend", "language": "python"}},
    {{"path": "main.py", "purpose": "API entrypoint and routes", "component": "backend", "language": "python"}},
    {{"path": "tests/test_main.py", "purpose": "Unit and integration tests", "component": "test", "language": "python"}}
  ]
}}

CRITICAL: Return ONLY valid JSON.
"""
        response = self.ask(prompt, format_json=True)
        try:
            data = response.parse_json()
            # Normalize file manifest (support both "file_manifest" and "files" keys)
            raw_manifest = data.get("file_manifest") or data.get("files") or []
            manifest = []
            for item in raw_manifest:
                if isinstance(item, dict) and "path" in item:
                    manifest.append(
                        FileEntry(
                            path=item.get("path"),
                            purpose=item.get("purpose", "Application component"),
                            component=item.get("component", "backend"),
                            language=item.get("language", "python"),
                        )
                    )

            if not manifest:
                manifest = [
                    FileEntry(path="models.py", purpose="Data structures and schemas", component="database", language="python"),
                    FileEntry(path="app.py", purpose="Core application logic and interface", component="backend", language="python"),
                    FileEntry(path="main.py", purpose="CLI / application entrypoint", component="backend", language="python"),
                    FileEntry(path="tests/test_app.py", purpose="Automated test suite", component="test", language="python"),
                ]

            return ProjectSpecification(
                project_name=data.get("project_name", "electorn_project"),
                tagline=data.get("tagline", "Autonomous AI Generated Application"),
                overview=data.get("overview", "A modular application built by Electorn AI."),
                tech_stack=data.get("tech_stack", {}),
                key_features=data.get("key_features", []),
                file_manifest=manifest,
                dependencies=data.get("dependencies", []),
                dev_dependencies=data.get("dev_dependencies", []),
                run_command=data.get("run_command", "python main.py"),
                test_command=data.get("test_command", "pytest"),
            )
        except Exception:
            # Resilient fallback architecture if parsing failed on small model
            sanitized_name = "electorn_app"
            return ProjectSpecification(
                project_name=sanitized_name,
                tagline="Generated application",
                overview=f"Automated build based on user prompt: {user_prompt}",
                tech_stack={"language": "Python", "framework": "Standard", "database": "SQLite", "testing": "pytest"},
                key_features=["Core logic", "Data persistence", "Automated tests"],
                file_manifest=[
                    FileEntry(path="models.py", purpose="Data structures and schemas", component="database", language="python"),
                    FileEntry(path="app.py", purpose="Core application logic and interface", component="backend", language="python"),
                    FileEntry(path="main.py", purpose="CLI / application entrypoint", component="backend", language="python"),
                    FileEntry(path="tests/test_app.py", purpose="Automated test suite", component="test", language="python"),
                ],
                dependencies=[],
                dev_dependencies=["pytest"],
                run_command="python main.py",
                test_command="pytest",
            )
