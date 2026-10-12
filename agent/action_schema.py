"""Structured schemas for tasks, actions, parameters, and verification evidence."""

from __future__ import annotations

import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Optional

from config.permissions import PermissionLevel


@dataclass
class TaskStep:
    """An individual atomic action within a workflow."""
    step_id: str = field(default_factory=lambda: f"step_{uuid.uuid4().hex[:6]}")
    action: str = ""
    parameters: dict[str, Any] = field(default_factory=dict)
    risk_level: PermissionLevel = PermissionLevel.LEVEL_1_SAFE
    requires_confirmation: bool = False
    description: str = ""
    status: str = "pending"  # "pending", "in_progress", "completed", "failed", "skipped"
    result: Optional[str] = None
    verification_evidence: Optional[str] = None
    duration_ms: int = 0
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TaskPlan:
    """A validated, ordered sequence of actions to fulfill an objective."""
    task_id: str = field(default_factory=lambda: f"task_{uuid.uuid4().hex[:8]}")
    original_transcript: str = ""
    objective: str = ""
    steps: list[TaskStep] = field(default_factory=list)
    current_step_index: int = 0
    status: str = "created"  # "created", "planned", "running", "paused", "completed", "failed", "cancelled"
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    error_message: Optional[str] = None
    verification_summary: str = ""
    is_cancelled: bool = False

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["steps"] = [s.to_dict() for s in self.steps]
        return d


@dataclass
class ExecutionResult:
    """Outcome of an executed task or workflow."""
    task_id: str
    success: bool
    message: str
    spoken_summary: str
    steps_completed: int
    total_steps: int
    duration_sec: float
    error: Optional[str] = None
    verification_passed: bool = True
