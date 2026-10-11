"""Project state representation, architecture manifest, and blueprint."""

from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field


class FileEntry(BaseModel):
    """File specification within the project architecture."""

    path: str
    purpose: str
    component: str  # e.g., "frontend", "backend", "db", "test", "config"
    language: Optional[str] = None
    created: bool = False


class ProjectSpecification(BaseModel):
    """Comprehensive blueprint designed by Architect Agent."""

    project_name: str
    tagline: str
    overview: str
    tech_stack: dict[str, str] = Field(
        default_factory=lambda: {
            "language": "Python",
            "framework": "FastAPI",
            "database": "SQLite",
            "testing": "pytest",
        }
    )
    architecture_overview: str = ""
    key_features: list[str] = Field(default_factory=list)
    file_manifest: list[FileEntry] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    dev_dependencies: list[str] = Field(default_factory=list)
    run_command: str = "python main.py"
    test_command: str = "pytest"


class ProjectState(BaseModel):
    """Live state of the active development workspace."""

    prompt: str
    specification: Optional[ProjectSpecification] = None
    created_files: list[str] = Field(default_factory=list)
    modified_files: list[str] = Field(default_factory=list)
    verified_files: list[str] = Field(default_factory=list)
    last_error: Optional[str] = None
    active_agent: Optional[str] = None
    is_completed: bool = False
    context_notes: dict[str, Any] = Field(default_factory=dict)

    def mark_file_created(self, path: str) -> None:
        if path not in self.created_files:
            self.created_files.append(path)

    def get_file_summary(self) -> str:
        """Compact summary of files for small-model context minimization."""
        if not self.created_files:
            return "No files created yet."
        return "\n".join(f"- {f}" for f in self.created_files)
