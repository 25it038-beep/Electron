"""Quality Controller supporting Economy, Professional, and Maximum Quality modes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class QualityProfile:
    mode_name: str
    max_search_queries: int
    deep_technical_review: bool
    multi_pass_anti_repetition: bool
    token_budget: int
    timeout_seconds: float


QUALITY_PROFILES = {
    "economy": QualityProfile(
        mode_name="economy",
        max_search_queries=1,
        deep_technical_review=False,
        multi_pass_anti_repetition=False,
        token_budget=2048,
        timeout_seconds=25.0,
    ),
    "professional": QualityProfile(
        mode_name="professional",
        max_search_queries=3,
        deep_technical_review=True,
        multi_pass_anti_repetition=True,
        token_budget=4096,
        timeout_seconds=45.0,
    ),
    "maximum": QualityProfile(
        mode_name="maximum",
        max_search_queries=5,
        deep_technical_review=True,
        multi_pass_anti_repetition=True,
        token_budget=8192,
        timeout_seconds=60.0,
    ),
}


def get_quality_profile(mode_name: str) -> QualityProfile:
    """Retrieve quality profile or default to professional."""
    clean = (mode_name or "professional").strip().lower()
    return QUALITY_PROFILES.get(clean, QUALITY_PROFILES["professional"])
