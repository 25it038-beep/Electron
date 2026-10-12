"""Unit and Integration tests for NVIDIA Multi-Model PowerPoint Engine."""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from typer.testing import CliRunner

from electorn.cli import app
from electorn.ppt.anti_repetition import AntiRepetitionController
from electorn.ppt.model_registry import NvidiaModelRegistry, PRESENTATION_ROLES
from electorn.ppt.multi_model_orchestrator import NvidiaPresentationOrchestrator
from electorn.ppt.nvidia_client import (
    NvidiaAuthenticationError,
    NvidiaCloudClient,
)
from electorn.ppt.quality_controller import get_quality_profile
from electorn.ppt.schema import (
    PresentationDeckPlan,
    PresentationStyle,
    SlideContent,
    SlideLayoutType,
)

runner = CliRunner()


def test_nvidia_client_missing_key():
    """Verify NvidiaCloudClient raises error when initialized without credentials."""
    client = NvidiaCloudClient(api_key="")
    assert client.is_configured is False
    with pytest.raises(NvidiaAuthenticationError):
        client.chat_completion(model="meta/llama-3.2-11b-vision-instruct", messages=[])


def test_nvidia_client_json_extraction():
    """Verify JSON block extraction handles markdown fences and raw text."""
    raw_markdown = "```json\n{\"status\": \"ok\", \"count\": 5}\n```"
    extracted = NvidiaCloudClient._extract_json_block(raw_markdown)
    assert extracted == '{"status": "ok", "count": 5}'

    raw_text = "Here is the response: {\"status\": \"verified\"} have a good day."
    extracted_text = NvidiaCloudClient._extract_json_block(raw_text)
    assert extracted_text == '{"status": "verified"}'


def test_model_registry_roles_and_overrides(monkeypatch):
    """Verify all 6 specialized multi-model roles exist and accept overrides."""
    registry = NvidiaModelRegistry()
    assert len(PRESENTATION_ROLES) == 6
    for role in [
        "lead_reasoning",
        "research",
        "storytelling",
        "technical_analysis",
        "design_planner",
        "quality_review",
    ]:
        assert role in PRESENTATION_ROLES
        assert registry.get_model_for_role(role) != ""

    # Test explicit override
    override = registry.get_model_for_role("lead_reasoning", global_override="custom/model-x")
    assert override == "custom/model-x"

    # Test env override
    monkeypatch.setenv("ELECTORN_PPT_MODEL", "env/specialized-model")
    assert registry.get_model_for_role("storytelling") == "env/specialized-model"


def test_quality_profiles():
    """Verify economy, professional, and maximum quality profiles."""
    p_eco = get_quality_profile("economy")
    p_pro = get_quality_profile("professional")
    p_max = get_quality_profile("maximum")

    assert p_eco.mode_name == "economy"
    assert p_pro.mode_name == "professional"
    assert p_max.mode_name == "maximum"
    assert p_max.token_budget > p_pro.token_budget >= p_eco.token_budget


def test_anti_repetition_detection_and_repair():
    """Verify AntiRepetitionController flags duplicate slides and applies bounded repair."""
    # Deck with repeated content on Slide 2 and Slide 3
    duplicated_deck = PresentationDeckPlan(
        topic="Relational Database Engines",
        target_slide_count=4,
        style=PresentationStyle.ACADEMIC,
        slides=[
            SlideContent(
                slide_number=1,
                layout_type=SlideLayoutType.TITLE,
                title="Relational Database Engines",
                subtitle="Academic Lecture",
            ),
            SlideContent(
                slide_number=2,
                layout_type=SlideLayoutType.EDITORIAL,
                title="Relational Database Architecture",
                bullets=[
                    "B-tree index scanning algorithms for fast disk lookups",
                    "Buffer pool management and page cache memory eviction",
                    "Write-ahead logging protocol for ACID transaction durability",
                ],
            ),
            SlideContent(
                slide_number=3,
                layout_type=SlideLayoutType.EDITORIAL,
                title="Database System Architecture",
                bullets=[
                    "B-tree index scanning algorithms for fast disk lookups",
                    "Buffer pool management and page cache memory eviction",
                    "Write-ahead logging protocol for ACID transaction durability",
                ],
            ),
            SlideContent(
                slide_number=4,
                layout_type=SlideLayoutType.CLOSING,
                title="Conclusion",
                bullets=["Summary of engine concepts"],
            ),
        ],
    )

    audit = AntiRepetitionController.audit_deck(duplicated_deck, threshold=0.6)
    assert audit.is_clean is False
    assert len(audit.duplication_issues) >= 1

    # Apply repair
    repaired_deck, new_audit = AntiRepetitionController.apply_bounded_repair(duplicated_deck)
    assert repaired_deck.slides[2].title != duplicated_deck.slides[1].title
    assert "Deep Dive" in repaired_deck.slides[2].title


def test_nvidia_orchestrator_mocked_execution():
    """Verify multi-model orchestrator executes collaboration pipeline."""
    mock_client = MagicMock()
    mock_client.is_configured = True
    mock_client.chat_completion.side_effect = [
        # 1. Topic brief
        '{"subject": "Distributed Mesh", "scope": "Ingress", "audience": "devs", "objective": "deploy"}',
        # 2. Slide narratives
        '{"slides": ['
        '{"slide_number": 1, "layout_type": "title", "title": "Mesh", "subtitle": "Deep Dive", "bullets": []},'
        '{"slide_number": 2, "layout_type": "editorial", "title": "Overview", "subtitle": "Core", "bullets": ["Point A", "Point B", "Point C", "Point D"]},'
        '{"slide_number": 3, "layout_type": "statistics", "title": "Telemetry", "subtitle": "Data", "bullets": ["Metric 1", "Metric 2"]},'
        '{"slide_number": 4, "layout_type": "closing", "title": "Conclusion", "subtitle": "Q&A", "bullets": ["End"]}'
        ']}',
        # 3. Tech review
        "Technical audit approved.",
    ]

    orchestrator = NvidiaPresentationOrchestrator(client=mock_client)
    plan = orchestrator.orchestrate_presentation(
        topic="Distributed Mesh Architecture",
        target_slide_count=4,
        style=PresentationStyle.PREMIUM_DARK,
        use_web_search=False,
        quality_mode="professional",
    )

    assert isinstance(plan, PresentationDeckPlan)
    assert len(plan.slides) == 4
    assert plan.manifest_metadata["provider"] == "nvidia_cloud"
    assert plan.manifest_metadata["orchestration_mode"] == "professional"


def test_cli_models_and_doctor():
    """Verify electorn ppt models and electorn ppt doctor commands."""
    res_models = runner.invoke(app, ["ppt", "models"])
    assert res_models.exit_code == 0
    assert "NVIDIA Multi-Model Presentation Registry" in res_models.stdout

    res_doctor = runner.invoke(app, ["ppt", "doctor"])
    assert res_doctor.exit_code == 0
    assert "Electorn Presentation Doctor" in res_doctor.stdout


def test_cli_ppt_options_help():
    """Verify electorn ppt CLI exposes new --provider, --mode, and --model flags."""
    result = runner.invoke(app, ["ppt", "--help"])
    assert result.exit_code == 0
    assert "--provider" in result.stdout
    assert "--mode" in result.stdout
    assert "--model" in result.stdout
