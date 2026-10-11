"""Project-specific persistent memory tracking engineering decisions, stack, and tasks."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional
from pydantic import BaseModel, Field


class ProjectMemoryData(BaseModel):
    """Structured engineering context for a single project workspace."""

    project_purpose: str = ""
    tech_stack: dict[str, str] = Field(default_factory=dict)
    architectural_decisions: list[str] = Field(default_factory=list)
    directory_conventions: list[str] = Field(default_factory=list)
    build_and_test_commands: dict[str, str] = Field(default_factory=dict)
    known_issues: list[str] = Field(default_factory=list)
    completed_tasks: list[str] = Field(default_factory=list)
    unfinished_tasks: list[str] = Field(default_factory=list)
    user_preferences: dict[str, Any] = Field(default_factory=dict)


class ProjectMemory:
    """Manages reading, updating, and clearing persistent engineering memory in .electorn/memory.json."""

    def __init__(self, workspace_root: Path | str):
        self.workspace_root = Path(workspace_root).resolve()
        self.memory_dir = self.workspace_root / ".electorn"
        self.memory_file = self.memory_dir / "memory.json"
        self.data: ProjectMemoryData = self.load()

    def load(self) -> ProjectMemoryData:
        """Load persistent memory from disk, returning defaults if non-existent."""
        if not self.memory_file.exists():
            return ProjectMemoryData()

        try:
            raw = json.loads(self.memory_file.read_text(encoding="utf-8"))
            return ProjectMemoryData(**raw)
        except Exception:
            return ProjectMemoryData()

    def save(self) -> None:
        """Persist memory data safely to .electorn/memory.json."""
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        # Filter potential secrets before serialization
        clean_dict = self.data.model_dump()
        self.memory_file.write_text(json.dumps(clean_dict, indent=2), encoding="utf-8")

    def update(
        self,
        purpose: Optional[str] = None,
        stack_updates: Optional[dict[str, str]] = None,
        decision: Optional[str] = None,
        convention: Optional[str] = None,
        commands: Optional[dict[str, str]] = None,
        completed_task: Optional[str] = None,
        unfinished_task: Optional[str] = None,
        issue: Optional[str] = None,
        preference: Optional[tuple[str, Any]] = None,
    ) -> None:
        """Record incremental engineering decisions."""
        if purpose:
            self.data.project_purpose = purpose
        if stack_updates:
            self.data.tech_stack.update(stack_updates)
        if decision and decision not in self.data.architectural_decisions:
            self.data.architectural_decisions.append(decision)
        if convention and convention not in self.data.directory_conventions:
            self.data.directory_conventions.append(convention)
        if commands:
            self.data.build_and_test_commands.update(commands)
        if completed_task:
            if completed_task not in self.data.completed_tasks:
                self.data.completed_tasks.append(completed_task)
            if completed_task in self.data.unfinished_tasks:
                self.data.unfinished_tasks.remove(completed_task)
        if unfinished_task and unfinished_task not in self.data.unfinished_tasks:
            self.data.unfinished_tasks.append(unfinished_task)
        if issue and issue not in self.data.known_issues:
            self.data.known_issues.append(issue)
        if preference:
            k, v = preference
            self.data.user_preferences[k] = v

        self.save()

    def clear(self) -> None:
        """Wipe memory back to clean slate."""
        self.data = ProjectMemoryData()
        if self.memory_file.exists():
            self.memory_file.unlink()

    def to_context_string(self) -> str:
        """Format memory into a concise system prompt context."""
        if not self.data.project_purpose and not self.data.tech_stack:
            return ""

        lines = ["[PROJECT MEMORY]"]
        if self.data.project_purpose:
            lines.append(f"Purpose: {self.data.project_purpose}")
        if self.data.tech_stack:
            lines.append(f"Tech Stack: {', '.join(f'{k}: {v}' for k, v in self.data.tech_stack.items())}")
        if self.data.architectural_decisions:
            lines.append("Key Decisions:")
            for d in self.data.architectural_decisions[-4:]:
                lines.append(f"  • {d}")
        if self.data.build_and_test_commands:
            lines.append("Commands: " + ", ".join(f"{k}='{v}'" for k, v in self.data.build_and_test_commands.items()))
        lines.append("[END PROJECT MEMORY]\n")
        return "\n".join(lines)
