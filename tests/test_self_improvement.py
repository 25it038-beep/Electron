"""Unit tests for SystemSelfImprovementAgent (audits, sandboxed patch verification, backups)."""

import tempfile
from pathlib import Path
import pytest

from electorn.verification.improvement_agent import (
    SystemSelfImprovementAgent,
    DiagnosisReport,
    ProposedPatch,
)


def test_system_diagnose():
    agent = SystemSelfImprovementAgent()
    diag = agent.diagnose_system()
    assert isinstance(diag, DiagnosisReport)
    assert 0 <= diag.health_score <= 100
    assert "runtimes" in diag.model_dump()
    assert "psutil" in diag.runtimes


def test_patch_proposal_syntax_check():
    agent = SystemSelfImprovementAgent()
    with tempfile.TemporaryDirectory() as tmp_dir:
        test_file = Path(tmp_dir) / "sample.py"
        test_file.write_text("def greet():\n    return 'hello'\n", encoding="utf-8")

        # 1. Valid syntax patch
        valid_code = "def greet():\n    return 'hello, Harshan'\n"
        patch1 = agent.propose_patch("patch_01", test_file, valid_code)
        assert patch1.is_verified_safe is True
        assert "+++ b/sample.py" in patch1.diff

        # 2. Invalid syntax patch
        invalid_code = "def greet(:\n    return 'broken'\n"
        patch2 = agent.propose_patch("patch_02", test_file, invalid_code)
        assert patch2.is_verified_safe is False
        assert any("Syntax error" in note for note in patch2.safety_notes)


def test_patch_blocks_prohibited_patterns():
    agent = SystemSelfImprovementAgent()
    with tempfile.TemporaryDirectory() as tmp_dir:
        test_file = Path(tmp_dir) / "sample.py"
        test_file.write_text("x = 10\n", encoding="utf-8")

        unsafe_code = "__import__('os').system('calc')\n"
        patch = agent.propose_patch("patch_unsafe", test_file, unsafe_code)
        assert patch.is_verified_safe is False
        assert any("Prohibited unsafe pattern" in note for note in patch.safety_notes)


def test_patch_application_with_backup():
    agent = SystemSelfImprovementAgent()
    with tempfile.TemporaryDirectory() as tmp_dir:
        test_file = Path(tmp_dir) / "sample.py"
        orig_content = "def add(a, b):\n    return a + b\n"
        test_file.write_text(orig_content, encoding="utf-8")

        new_content = "def add(a, b):\n    # Optimized addition\n    return a + b\n"
        patch = agent.propose_patch("patch_opt", test_file, new_content)
        assert patch.is_verified_safe is True

        res = agent.apply_patch(patch, new_content)
        assert res["success"] is True

        # Check target was updated
        assert test_file.read_text(encoding="utf-8") == new_content

        # Check backup was created with original content
        backup = Path(res["backup_path"])
        assert backup.exists()
        assert backup.read_text(encoding="utf-8") == orig_content
