"""Unit tests for WindowsOSAgent (system diagnostics, guarded execution, file organization)."""

from pathlib import Path
import tempfile
import pytest

from electorn.automation.os_agent import WindowsOSAgent


def test_os_agent_diagnostics():
    agent = WindowsOSAgent()
    diag = agent.get_system_diagnostics()
    assert "cpu" in diag
    assert "memory" in diag
    assert "drives" in diag
    assert "os" in diag
    assert isinstance(diag["memory"], dict)
    assert "total_gb" in diag["memory"]


def test_os_agent_safe_command_execution():
    agent = WindowsOSAgent()
    res = agent.execute_command_safely("powershell -Command Write-Output 'ELECTORN_TEST_OK'")
    assert res["success"] is True
    assert "ELECTORN_TEST_OK" in res["stdout"]


def test_os_agent_blocks_destructive_commands():
    agent = WindowsOSAgent()
    destructive_cmds = [
        "format C: /y",
        "rmdir /s /q C:\\Windows",
        "del /f /q /s C:\\Windows\\System32",
        "powershell -Command Remove-Item -Recurse -Force C:\\",
    ]
    for cmd in destructive_cmds:
        res = agent.execute_powershell_guarded(cmd)
        assert res["blocked"] is True, f"Failed to block destructive command: {cmd}"
        assert "Security guardrail violation" in res["reason"]


def test_os_agent_organize_directory_dry_run():
    agent = WindowsOSAgent()
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        # Create test dummy files
        (tmp_path / "report.pdf").write_text("dummy pdf", encoding="utf-8")
        (tmp_path / "script.py").write_text("print('hello')", encoding="utf-8")
        (tmp_path / "photo.png").write_text("fake image", encoding="utf-8")
        (tmp_path / "archive.zip").write_text("fake zip", encoding="utf-8")

        summary = agent.organize_directory(target_dir=tmp_path, dry_run=True)
        assert summary["success"] is True
        assert summary["dry_run"] is True
        assert summary["files_moved"] == 4

        # Verify files were NOT moved in dry run
        assert (tmp_path / "report.pdf").exists()
        assert (tmp_path / "script.py").exists()


def test_os_agent_organize_directory_live():
    agent = WindowsOSAgent()
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        (tmp_path / "doc.docx").write_text("doc content", encoding="utf-8")
        (tmp_path / "song.mp3").write_text("audio content", encoding="utf-8")

        summary = agent.organize_directory(target_dir=tmp_path, dry_run=False)
        assert summary["success"] is True
        assert summary["files_moved"] == 2
        assert (tmp_path / "Documents" / "doc.docx").exists()
        assert (tmp_path / "Media" / "song.mp3").exists()
