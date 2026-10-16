"""Unit tests for ProactiveResearchMonitor (interests, hash deduplication, briefings)."""

import tempfile
from pathlib import Path
import pytest

from electorn.monitoring.research_monitor import (
    ProactiveResearchMonitor,
    MonitoredInterest,
    DiscoveredItem,
)


def test_monitor_deduplication():
    with tempfile.TemporaryDirectory() as tmp_dir:
        storage = Path(tmp_dir)
        monitor = ProactiveResearchMonitor(storage_dir=storage)

        url = "https://github.com/trending/python"
        assert monitor.is_duplicate(url) is False

        # Mark seen
        item = DiscoveredItem(
            title="Trending Python",
            url=url,
            summary="New repositories in Python",
            category="developer_tools",
            relevance_score=0.9,
        )
        monitor.record_discovery(item)

        # Second check should detect duplicate
        assert monitor.is_duplicate(url) is True


def test_monitor_interest_management():
    with tempfile.TemporaryDirectory() as tmp_dir:
        storage = Path(tmp_dir)
        monitor = ProactiveResearchMonitor(storage_dir=storage)

        initial_count = len(monitor.get_active_interests())
        monitor.add_interest(
            topic="Quantum Computing Algorithms",
            category="physics_ai",
            keywords=["qubit", "quantum supremacy", "qiskit"],
        )
        updated = monitor.get_active_interests()
        assert len(updated) == initial_count + 1
        assert any(i.topic == "Quantum Computing Algorithms" for i in updated)


def test_morning_briefing_generation():
    with tempfile.TemporaryDirectory() as tmp_dir:
        storage = Path(tmp_dir)
        monitor = ProactiveResearchMonitor(storage_dir=storage)

        # Add a test discovery
        monitor.record_discovery(DiscoveredItem(
            title="Llama 3 Released",
            url="https://ai.meta.com/llama3",
            summary="Next generation open weight LLM",
            category="ai_models",
            relevance_score=0.95,
        ))

        briefing = monitor.generate_morning_briefing(user_name="Harshan")
        assert "Harshan" in briefing
        assert "Morning Briefing" in briefing
        assert "Llama 3 Released" in briefing
