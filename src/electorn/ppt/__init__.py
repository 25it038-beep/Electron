"""Electorn AI PowerPoint generation package."""

from electorn.ppt.builder import PowerPointBuilder
from electorn.ppt.design import THEMES, DesignTheme, get_theme
from electorn.ppt.document_ingestion import DocumentAnalysis, DocumentIngestionEngine
from electorn.ppt.engine import PresentationEngine
from electorn.ppt.planner import PresentationPlanner
from electorn.ppt.schema import (
    KeyMetric,
    PresentationDeckPlan,
    PresentationStyle,
    ProcessStep,
    SlideContent,
    SlideLayoutType,
    TableData,
    TimelineItem,
)
from electorn.ppt.validator import PresentationQAReport, PresentationQAValidator

__all__ = [
    "PresentationEngine",
    "PresentationPlanner",
    "PowerPointBuilder",
    "PresentationQAValidator",
    "DocumentIngestionEngine",
    "DocumentAnalysis",
    "PresentationDeckPlan",
    "SlideContent",
    "SlideLayoutType",
    "PresentationStyle",
    "KeyMetric",
    "ProcessStep",
    "TimelineItem",
    "TableData",
    "get_theme",
    "THEMES",
]
