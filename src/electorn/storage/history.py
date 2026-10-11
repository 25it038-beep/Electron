"""Execution history and project session logging."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Optional
from pydantic import BaseModel, Field


class AgentActionLog(BaseModel):
    """Log entry for an individual agent step."""

    timestamp: float = Field(default_factory=time.time)
    agent_name: str
    role: str
    action_type: str  # e.g., "plan", "code_gen", "test", "repair"
    summary: str
    files_affected: list[str] = Field(default_factory=list)
    success: bool = True
    details: Optional[dict[str, Any]] = None


class SessionHistory(BaseModel):
    """Full session audit record for an Electorn run."""

    session_id: str
    prompt: str
    model_used: str
    created_at: float = Field(default_factory=time.time)
    completed_at: Optional[float] = None
    status: str = "in_progress"  # "in_progress", "completed", "failed"
    actions: list[AgentActionLog] = Field(default_factory=list)
    repair_count: int = 0
    workspace_dir: str = "."

    def record_action(
        self,
        agent_name: str,
        role: str,
        action_type: str,
        summary: str,
        files_affected: Optional[list[str]] = None,
        success: bool = True,
        details: Optional[dict[str, Any]] = None,
    ) -> AgentActionLog:
        """Append an agent action to the session history."""
        log = AgentActionLog(
            agent_name=agent_name,
            role=role,
            action_type=action_type,
            summary=summary,
            files_affected=files_affected or [],
            success=success,
            details=details,
        )
        self.actions.append(log)
        return log

    def save(self, workspace_path: Path | str) -> Path:
        """Persist session history to .electorn/sessions/<session_id>.json."""
        target_dir = Path(workspace_path) / ".electorn" / "sessions"
        target_dir.mkdir(parents=True, exist_ok=True)
        file_path = target_dir / f"{self.session_id}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(self.model_dump_json(indent=2))
        return file_path
