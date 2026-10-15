"""Automated unit and integration test suite for Electorn Personal Communication Assistant."""

from datetime import datetime, timezone
import json
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from typer.testing import CliRunner

from electorn.assistant.calling import MockTelephonyProvider, TwilioTelephonyProvider
from electorn.assistant.cli import assistant_app
from electorn.assistant.email_connector import GmailConnector
from electorn.assistant.file_intelligence import FileIntelligenceEngine, FileSecurityError
from electorn.assistant.permissions import PermissionEngine, SecurityPolicyError
from electorn.assistant.schema import (
    ActionItem,
    ActionStatus,
    AssistantConfig,
    CallBriefing,
    ChannelType,
    ExtractedTask,
    MessageRecord,
    PermissionMode,
    TaskPriority,
    TaskStatus,
)
from electorn.assistant.storage import AssistantStorage
from electorn.assistant.supervisor import AssistantSupervisor
from electorn.assistant.tasks import TaskEngine
from electorn.assistant.whatsapp_connector import WhatsAppConnector

runner = CliRunner()


# =============================================================================
# 1. PERMISSION SYSTEM & SAFETY BOUNDARIES
# =============================================================================

def test_permissions_observe_mode_blocks_outbound():
    """Verify OBSERVE mode blocks consequential outbound messages and calls."""
    cfg = AssistantConfig(permission_mode=PermissionMode.OBSERVE)
    engine = PermissionEngine(cfg)

    action = ActionItem(
        action_type="send_email",
        channel=ChannelType.GMAIL,
        recipient="partner@example.com",
        content="Meeting confirmed",
        status=ActionStatus.APPROVED,
    )
    with pytest.raises(SecurityPolicyError, match="prohibited in OBSERVE mode"):
        engine.is_action_allowed(action)


def test_permissions_assist_mode_requires_explicit_approval():
    """Verify ASSIST mode forbids unapproved action execution."""
    cfg = AssistantConfig(permission_mode=PermissionMode.ASSIST)
    engine = PermissionEngine(cfg)

    unapproved = ActionItem(
        action_type="send_whatsapp",
        channel=ChannelType.WHATSAPP,
        recipient="+14155551234",
        content="Draft text",
        status=ActionStatus.PENDING_APPROVAL,
    )
    assert engine.is_action_allowed(unapproved) is False
    with pytest.raises(SecurityPolicyError, match="requires explicit user approval"):
        engine.check_and_authorize(unapproved)

    # When approved:
    unapproved.status = ActionStatus.APPROVED
    assert engine.is_action_allowed(unapproved) is True
    assert engine.check_and_authorize(unapproved) is True


def test_emergency_killswitch_pause():
    """Verify is_paused freezes all actions regardless of approval status."""
    cfg = AssistantConfig(is_paused=True, permission_mode=PermissionMode.CONTROLLED)
    engine = PermissionEngine(cfg)

    action = ActionItem(
        action_type="send_email",
        channel=ChannelType.GMAIL,
        recipient="test@example.com",
        content="Important",
        status=ActionStatus.APPROVED,
    )
    with pytest.raises(SecurityPolicyError, match="currently PAUSED"):
        engine.is_action_allowed(action)


# =============================================================================
# 2. FILE INTELLIGENCE & PATH TRAVERSAL DEFENSE
# =============================================================================

def test_path_traversal_protection(tmp_path: Path):
    """Verify directory traversal payloads in attachment filenames are neutralized."""
    engine = FileIntelligenceEngine(download_dir=tmp_path)
    
    # Path traversal attack vectors
    malicious_names = ["../../../../etc/passwd", "..\\..\\windows\\system32\\cmd.exe", "nested/../../secret.txt"]
    for mal in malicious_names:
        safe_path = engine.sanitize_path(mal)
        assert safe_path.parent == tmp_path
        assert ".." not in safe_path.name


def test_magic_byte_mime_detection(tmp_path: Path):
    """Verify content inspection over extension spoofing."""
    engine = FileIntelligenceEngine(download_dir=tmp_path)

    # Fake PDF: named text.pdf but contains PNG magic bytes
    fake_pdf = tmp_path / "spoofed.pdf"
    fake_pdf.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR...")
    detected = engine.detect_real_mime(fake_pdf)
    assert detected == "image/png"


def test_file_analysis_csv_and_text(tmp_path: Path):
    """Verify structural and action extraction from CSV and text files."""
    engine = FileIntelligenceEngine(download_dir=tmp_path)

    sample_csv = tmp_path / "project_timeline.csv"
    sample_csv.write_text(
        "Task,Owner,Deadline\n"
        "Security Audit,Harshan,due: October 20th\n"
        "Cloud Migration,DevTeam,deadline: 11/15/2026\n",
        encoding="utf-8"
    )

    report = engine.analyze_file(sample_csv)
    assert report.detected_mime == "text/csv" or "csv" in report.detected_mime
    assert len(report.deadlines_and_actions) >= 1
    assert any("October 20th" in d or "11/15/2026" in d for d in report.deadlines_and_actions)


# =============================================================================
# 3. WHATSAPP WEBHOOK VALIDATION & HMAC SIGNATURES
# =============================================================================

def test_whatsapp_webhook_verification():
    """Verify Meta challenge handshake validation."""
    connector = WhatsAppConnector(verify_token="electorn_test_secret")
    assert connector.verify_webhook("subscribe", "electorn_test_secret", "challenge_1234") == "challenge_1234"
    assert connector.verify_webhook("subscribe", "wrong_token", "challenge_1234") is None


def test_whatsapp_hmac_signature_validation():
    """Verify SHA-256 HMAC signature verification on incoming webhooks."""
    connector = WhatsAppConnector(app_secret="test_meta_app_secret")
    payload = b'{"object": "whatsapp_business_account"}'
    
    import hmac, hashlib
    valid_sig = "sha256=" + hmac.new(b"test_meta_app_secret", payload, hashlib.sha256).hexdigest()
    assert connector.validate_signature(payload, valid_sig) is True
    assert connector.validate_signature(payload, "sha256=invalid_hash_signature") is False


# =============================================================================
# 4. TASK ENGINE EXTRACTION & DEDUPLICATION
# =============================================================================

def test_task_extraction_and_priorities():
    """Verify natural commitment parsing and priority estimation."""
    engine = TaskEngine()
    sample_text = (
        "Hi Harshan,\n"
        "Please ensure the cloud deployment is configured by October 25th.\n"
        "This is urgent and critical: patch the open SSL vulnerability ASAP.\n"
        "Also todo: update documentation when possible.\n"
    )

    tasks = engine.extract_tasks_from_text(sample_text, source_type="email", source_id="msg-101")
    assert len(tasks) >= 2
    critical_tasks = [t for t in tasks if t.priority == TaskPriority.CRITICAL]
    assert len(critical_tasks) >= 1
    assert "patch the open ssl" in critical_tasks[0].title.lower()


def test_task_deduplication():
    """Verify identical commitments are collapsed and merged."""
    engine = TaskEngine()
    tasks = [
        ExtractedTask(title="Update API Documentation", priority=TaskPriority.LOW),
        ExtractedTask(title="update api documentation!", priority=TaskPriority.HIGH, deadline="Friday"),
    ]
    deduped = engine.deduplicate_tasks(tasks)
    assert len(deduped) == 1
    assert deduped[0].priority == TaskPriority.HIGH
    assert deduped[0].deadline == "Friday"


# =============================================================================
# 5. CALLING AGENT & TRUTHFUL DISCLOSURES
# =============================================================================

def test_mock_telephony_provider_truthful_disclosure():
    """Verify simulated provider clearly distinguishes simulation from PSTN calls."""
    provider = MockTelephonyProvider()
    caps = provider.get_capabilities()
    assert caps["real_telephony"] is False
    assert caps["outbound_pstn_calls"] is False

    briefing = provider.prepare_briefing("Marcus Vance", "+14155550199", "Q4 Architecture Review")
    assert "automated assistant calling on behalf of" in briefing.proposed_opening

    call_record = provider.initiate_call(briefing)
    assert call_record.is_simulated is True
    assert call_record.status == "completed"
    assert len(call_record.follow_up_tasks) >= 1


# =============================================================================
# 6. REPLY AGENT DRAFT & REJECT WORKFLOW
# =============================================================================

def test_reply_drafting_and_reject_workflow(tmp_path: Path):
    """Verify drafting does not auto-send and rejection cancels action."""
    storage = AssistantStorage(base_dir=tmp_path)
    msg = MessageRecord(
        message_id="msg-999",
        channel=ChannelType.GMAIL,
        sender="client@acme.corp",
        recipient="me",
        subject="Scope inquiry",
        body_text="Can we discuss the project deliverables?",
    )
    storage.save_message(msg)

    supervisor = AssistantSupervisor()
    supervisor.storage = storage

    action = supervisor.draft_reply("msg-999", style_override="concise")
    assert action.status == ActionStatus.PENDING_APPROVAL
    assert action.recipient == "client@acme.corp"
    assert "Re: Scope inquiry" in action.subject

    # Rejection cancels action
    rejected = supervisor.reject_action(action.action_id, reason="Not relevant")
    assert rejected.status == ActionStatus.REJECTED
    assert rejected.execution_result == "Not relevant"


# =============================================================================
# 7. CLI COMMAND SMOKE TESTS
# =============================================================================

def test_cli_assistant_status():
    result = runner.invoke(assistant_app, ["status"])
    assert result.exit_code == 0
    assert "Electorn Personal AI Assistant" in result.output


def test_cli_assistant_calls_capabilities():
    result = runner.invoke(assistant_app, ["calls", "capabilities"])
    assert result.exit_code == 0
    assert "Telephony & Call Agent Capabilities" in result.output
