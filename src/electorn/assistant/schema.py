"""Data models and schemas for Electorn Advanced Personal Communication Agent."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
import uuid


class PermissionMode(str, Enum):
    """Operational permission modes for the Personal Assistant."""
    OBSERVE = "observe"          # Read-only: summarize, analyze files, extract tasks, notify
    ASSIST = "assist"            # Proactive drafts, call briefings, explicit approval required for all actions
    CONTROLLED = "controlled"    # Whitelisted pre-approved actions, audit log, emergency killswitch


class ActionStatus(str, Enum):
    """Approval lifecycle states for outgoing consequential actions."""
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ChannelType(str, Enum):
    """Supported communication channels."""
    GMAIL = "gmail"
    WHATSAPP = "whatsapp"
    CALL = "call"
    LOCAL_SYSTEM = "local_system"


class WritingStyle(str, Enum):
    """Configurable tone and writing styles for natural replies."""
    PROFESSIONAL = "professional"
    FRIENDLY = "friendly"
    CONCISE = "concise"
    FORMAL = "formal"
    CUSTOM = "custom"


class TaskPriority(str, Enum):
    """Task urgency and priority ranking."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TaskStatus(str, Enum):
    """Status lifecycle for automated extracted tasks."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SNOOZED = "snoozed"
    DISMISSED = "dismissed"


class AttachmentMetadata(BaseModel):
    """Metadata for message attachments."""
    attachment_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    filename: str
    content_type: str = "application/octet-stream"
    size_bytes: int = 0
    safe_local_path: Optional[str] = None
    sha256_hash: Optional[str] = None
    is_downloaded: bool = False
    source_message_id: Optional[str] = None
    download_timestamp: Optional[datetime] = None


class MessageRecord(BaseModel):
    """Standardized representation of incoming and outgoing communications."""
    message_id: str
    channel: ChannelType
    thread_id: Optional[str] = None
    sender: str
    recipient: str
    subject: Optional[str] = None
    body_text: str = ""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    raw_snippet: Optional[str] = None
    attachments: List[AttachmentMetadata] = Field(default_factory=list)
    has_links: bool = False
    is_read: bool = False
    is_archived: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ActionItem(BaseModel):
    """Extracted action item or promise from communications."""
    action_id: str = Field(default_factory=lambda: f"act-{uuid.uuid4().hex[:8]}")
    action_type: str             # "send_email", "send_whatsapp", "place_call", "run_code"
    channel: ChannelType
    recipient: str
    subject: Optional[str] = None
    content: str
    source_message_id: Optional[str] = None
    attachments: List[str] = Field(default_factory=list)
    status: ActionStatus = ActionStatus.PENDING_APPROVAL
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    approved_at: Optional[datetime] = None
    executed_at: Optional[datetime] = None
    execution_result: Optional[str] = None
    risk_level: str = "medium"   # low, medium, high


class ExtractedTask(BaseModel):
    """Actionable task extracted from conversations, files, or call briefings."""
    task_id: str = Field(default_factory=lambda: f"tsk-{uuid.uuid4().hex[:8]}")
    title: str
    description: str = ""
    source_type: str = "message" # message, file, call
    source_id: str = ""
    deadline: Optional[str] = None
    priority: TaskPriority = TaskPriority.MEDIUM
    confidence: float = 0.85
    status: TaskStatus = TaskStatus.PENDING
    assigned_to: str = "user"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    snoozed_until: Optional[datetime] = None
    tags: List[str] = Field(default_factory=list)


class DocumentAnalysisReport(BaseModel):
    """Comprehensive intelligence report for ingested documents."""
    file_path: str
    detected_mime: str
    file_size_bytes: int
    page_count: Optional[int] = None
    executive_summary: str
    key_findings: List[str] = Field(default_factory=list)
    extracted_data: Dict[str, Any] = Field(default_factory=dict)
    deadlines_and_actions: List[str] = Field(default_factory=list)
    inconsistencies_or_risks: List[str] = Field(default_factory=list)
    source_references: List[str] = Field(default_factory=list)
    limitations: Optional[str] = None
    is_partial_analysis: bool = False
    processed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CallBriefing(BaseModel):
    """Preparation dossier before placing or handling an outbound/inbound call."""
    briefing_id: str = Field(default_factory=lambda: f"brf-{uuid.uuid4().hex[:8]}")
    contact_name: str
    phone_number: str
    purpose: str
    proposed_opening: str
    key_talking_points: List[str] = Field(default_factory=list)
    anticipated_questions: List[str] = Field(default_factory=list)
    desired_outcome: str = ""
    provider_name: str = "telephony_gateway"
    estimated_cost: Optional[str] = None
    automated_disclosure_required: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CallRecord(BaseModel):
    """Audit and status record for placed or simulated calls."""
    call_id: str = Field(default_factory=lambda: f"call-{uuid.uuid4().hex[:8]}")
    contact_name: str
    phone_number: str
    purpose: str
    provider: str
    status: str                  # prepared, ringing, in_progress, completed, failed, cancelled
    is_simulated: bool = False
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_seconds: int = 0
    transcript: Optional[str] = None
    call_summary: Optional[str] = None
    follow_up_tasks: List[str] = Field(default_factory=list)


class AssistantConfig(BaseModel):
    """Persistent configuration for Electorn Personal Assistant."""
    permission_mode: PermissionMode = PermissionMode.ASSIST
    default_writing_style: WritingStyle = WritingStyle.PROFESSIONAL
    custom_style_instructions: Optional[str] = None
    auto_download_attachments: bool = True
    max_attachment_size_mb: int = 25
    downloads_directory: str = str(Path.home() / ".electorn" / "assistant" / "downloads")
    audit_log_path: str = str(Path.home() / ".electorn" / "assistant" / "audit.jsonl")
    quiet_hours_start: Optional[str] = "22:00"
    quiet_hours_end: Optional[str] = "07:00"
    is_paused: bool = False
    whitelisted_recipients: List[str] = Field(default_factory=list)
    gmail_enabled: bool = False
    whatsapp_enabled: bool = False
    telephony_provider: str = "mock" # mock, twilio, vapi
    telephony_api_key: Optional[str] = None
