import pytest
import tempfile
from pathlib import Path
from electorn.workspace.file_manager import FileManager
from electorn.workspace.permissions import PermissionManager
from electorn.workspace.project_state import FileEntry, ProjectSpecification, ProjectState


def test_file_manager_write_read_and_security():
    with tempfile.TemporaryDirectory() as tmp_dir:
        fm = FileManager(tmp_dir, permissions=PermissionManager(auto_approve=True))

        # Safe write inside workspace
        res = fm.write_file("src/main.py", "print('hello')\n")
        assert res.success is True
        assert res.action == "created"
        assert res.diff is None

        # Modify file and verify diff
        res2 = fm.write_file("src/main.py", "print('hello world')\n")
        assert res2.success is True
        assert res2.action == "modified"
        assert res2.diff is not None
        assert "+print('hello world')" in res2.diff

        # Read back
        content = fm.read_file("src/main.py")
        assert "hello world" in content

        # Security check: Path traversal prevention
        with pytest.raises(PermissionError):
            fm.resolve_safe_path("../../outside.txt")


def test_project_state():
    state = ProjectState(prompt="Build a CLI tool")
    state.mark_file_created("cli.py")
    state.mark_file_created("cli.py")  # duplicate check
    assert state.created_files == ["cli.py"]
    assert "cli.py" in state.get_file_summary()
