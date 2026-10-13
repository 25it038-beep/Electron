"""Structured intermediate representation models for PowerPoint generation in Electorn AI."""

from __future__ import annotations

from enum import Enum
from typing import Any, List, Optional
from pydantic import BaseModel, Field


class SlideLayoutType(str, Enum):
    TITLE = "title"
    SECTION_HEADER = "section_header"
    EDITORIAL = "editorial"
    TWO_COLUMN = "two_column"
    COMPARISON = "comparison"
    TIMELINE = "timeline"
    PROCESS = "process"
    ARCHITECTURE = "architecture"
    STATISTICS = "statistics"
    TABLE = "table"
    CODE = "code"
    REFERENCES = "references"
    CLOSING = "closing"


class PresentationStyle(str, Enum):
    PREMIUM_DARK = "premium-dark"
    MINIMALIST_LIGHT = "minimalist-light"
    ACADEMIC = "academic"
    RESEARCH = "research"
    CORPORATE_PITCH = "corporate-pitch"
    DATA_REPORT = "data-report"
    CINEMATIC = "cinematic"


class KeyMetric(BaseModel):
    value: str
    label: str
    description: Optional[str] = None


class TimelineItem(BaseModel):
    step: str
    title: str
    description: str


class ProcessStep(BaseModel):
    number: int
    title: str
    description: str


class ArchComponent(BaseModel):
    layer: str
    name: str
    items: List[str] = Field(default_factory=list)


class TableData(BaseModel):
    headers: List[str]
    rows: List[List[str]]


class ContentCard(BaseModel):
    tag: Optional[str] = None
    title: str
    body: str
    highlight: Optional[str] = None
    bullet_points: List[str] = Field(default_factory=list)


class SlideContent(BaseModel):
    slide_id: str = Field(default="")
    slide_number: int
    layout_type: SlideLayoutType
    title: str
    subtitle: Optional[str] = None
    category_badge: Optional[str] = None
    bullets: List[str] = Field(default_factory=list)
    paragraphs: List[str] = Field(default_factory=list)
    
    # Modern Gamma-style Cards and Callouts
    cards: List[ContentCard] = Field(default_factory=list)
    callout: Optional[str] = None
    callout_label: Optional[str] = None
    
    # Structural visual content
    left_column_title: Optional[str] = None
    left_column_bullets: List[str] = Field(default_factory=list)
    right_column_title: Optional[str] = None
    right_column_bullets: List[str] = Field(default_factory=list)
    
    metrics: List[KeyMetric] = Field(default_factory=list)
    timeline: List[TimelineItem] = Field(default_factory=list)
    process_steps: List[ProcessStep] = Field(default_factory=list)
    architecture: List[ArchComponent] = Field(default_factory=list)
    table: Optional[TableData] = None
    
    code_snippet: Optional[str] = None
    code_language: Optional[str] = None
    
    citations: List[str] = Field(default_factory=list)
    speaker_notes: Optional[str] = None


class PresentationDeckPlan(BaseModel):
    topic: str
    audience: str = "general"
    style: PresentationStyle = PresentationStyle.PREMIUM_DARK
    target_slide_count: int
    slides: List[SlideContent] = Field(default_factory=list)
    manifest_metadata: dict[str, Any] = Field(default_factory=dict)
