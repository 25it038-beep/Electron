"""Memory-efficient context manager for sequential agent execution."""

from __future__ import annotations

from typing import Optional
from electorn.workspace.file_manager import FileManager
from electorn.workspace.project_state import ProjectSpecification, ProjectState


class MemoryManager:
    """Controls and compacts context windows to maintain peak performance on small models (1B-4B)."""

    def __init__(self, file_manager: FileManager, max_context_chars: int = 12000):
        self.file_manager = file_manager
        self.max_context_chars = max_context_chars

    def build_agent_context(
        self,
        state: ProjectState,
        spec: ProjectSpecification,
        relevant_components: Optional[list[str]] = None,
    ) -> str:
        """Create a compact, highly relevant context snapshot for the active agent."""
        parts: list[str] = []

        # High-level architecture summary
        parts.append(f"Project: {spec.project_name} - {spec.tagline}")
        parts.append(f"Architecture: {spec.overview}")
        tech_str = ", ".join(f"{k}: {v}" for k, v in spec.tech_stack.items())
        parts.append(f"Tech Stack: {tech_str}")

        # Current workspace files
        file_tree = self.file_manager.get_directory_tree_str()
        parts.append(f"\nExisting Files in Workspace:\n{file_tree}")

        # Only inject full contents of directly relevant existing files
        relevant_files = []
        for entry in spec.file_manifest:
            if relevant_components and entry.component in relevant_components:
                relevant_files.append(entry.path)

        # Include contents of top relevant files up to memory budget
        budget_remaining = self.max_context_chars - sum(len(p) for p in parts)
        for f_path in relevant_files:
            try:
                content = self.file_manager.read_file(f_path)
                snippet = f"\n--- File: {f_path} ---\n{content}\n"
                if len(snippet) < budget_remaining:
                    parts.append(snippet)
                    budget_remaining -= len(snippet)
            except Exception:
                continue

        return "\n".join(parts)
