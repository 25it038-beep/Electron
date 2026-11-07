"""Data models and type definitions for HS Autonomous Computer Engine (HACE)."""

from __future__ import annotations

import time
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class RiskLevel(str, Enum):
    SAFE = "safe"
    LOW_RISK = "low_risk"
    HIGH_RISK_CONFIRM = "high_risk_confirm"
    BLOCKED = "blocked"


class TaskStatus(str, Enum):
    IDLE = "idle"
    PLANNING = "planning"
    IN_PROGRESS = "in_progress"
    WAITING_APPROVAL = "waiting_approval"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    ABORTED = "aborted"


@dataclass
class BoundingBox:
    x: int
    y: int
    width: int
    height: int


@dataclass
class UIElement:
    id: str = ""
    type: str = "button"
    label: str = ""
    location: Tuple[int, int] = (0, 0)
    bounds: Optional[BoundingBox] = None
    confidence: float = 0.95
    is_enabled: bool = True
    is_visible: bool = True
    element_id: Optional[str] = None
    element_type: Optional[str] = None
    center_x: Optional[int] = None
    center_y: Optional[int] = None
    bounding_box: Optional[Any] = None

    def __post_init__(self) -> None:
        if self.element_id and not self.id:
            self.id = self.element_id
        if self.element_type and not self.type:
            self.type = self.element_type
        if self.center_x is not None and self.center_y is not None:
            self.location = (self.center_x, self.center_y)
        elif self.location:
            self.center_x, self.center_y = self.location

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "label": self.label,
            "location": list(self.location),
            "bounds": asdict(self.bounds) if self.bounds else None,
            "confidence": self.confidence,
            "isEnabled": self.is_enabled,
            "isVisible": self.is_visible,
        }


@dataclass
class OCRToken:
    text: str
    location: Tuple[int, int]
    bounds: BoundingBox
    confidence: float = 0.9


@dataclass
class ComputerState:
    active_application: str = "Desktop"
    active_window: str = "Desktop"
    cursor_location: Tuple[int, int] = (0, 0)
    screen_resolution: Dict[str, int] = field(default_factory=lambda: {"width": 1920, "height": 1080})
    visible_elements: List[UIElement] = field(default_factory=list)
    ocr_tokens: List[OCRToken] = field(default_factory=list)
    task_status: str = "ready"
    automation_enabled: bool = True
    is_paused: bool = False
    emergency_stopped: bool = False
    last_action: Optional[str] = None
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "activeApplication": self.active_application,
            "activeWindow": self.active_window,
            "cursorLocation": list(self.cursor_location),
            "screenResolution": self.screen_resolution,
            "visibleElements": [e.to_dict() for e in self.visible_elements],
            "taskStatus": self.task_status,
            "automationEnabled": self.automation_enabled,
            "isPaused": self.is_paused,
            "emergencyStopped": self.emergency_stopped,
            "lastAction": self.last_action,
            "timestamp": self.timestamp,
        }


@dataclass
class ActionPayload:
    action_id: str = field(default_factory=lambda: f"act_{uuid.uuid4().hex[:6]}")
    category: str = "mouse"
    type: str = "click"
    action_type: Optional[str] = None
    target: Optional[str] = None
    coordinates: Optional[Tuple[int, int]] = None
    end_coordinates: Optional[Tuple[int, int]] = None
    text: Optional[str] = None
    keys: List[str] = field(default_factory=list)
    delta_x: int = 0
    delta_y: int = 0
    url: Optional[str] = None
    selector: Optional[str] = None
    timeout_ms: int = 5000
    description: str = ""
    risk_level: Any = "safe"
    requires_confirmation: bool = False
    parameters: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.action_type and not self.type:
            self.type = self.action_type
        elif self.type and not self.action_type:
            self.action_type = self.type


@dataclass
class ActionResult:
    action_id: str
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    duration_ms: float = 0.0
    screenshot_base64: Optional[str] = None


@dataclass
class TaskStep:
    step_id: str
    order: int
    description: str
    action: ActionPayload
    status: str = "pending"
    expected_outcome: str = ""
    verification_evidence: Optional[str] = None
    result: Optional[ActionResult] = None
    retry_count: int = 0
    error: Optional[str] = None


@dataclass
class TaskPlan:
    task_id: str = field(default_factory=lambda: f"hace_task_{uuid.uuid4().hex[:8]}")
    original_instruction: str = ""
    goal: str = ""
    target_application: str = "Desktop"
    steps: List[TaskStep] = field(default_factory=list)
    current_step_index: int = 0
    status: Any = "planned"
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    completed_time: Optional[float] = None
    error: Optional[str] = None
    summary: Optional[str] = None
