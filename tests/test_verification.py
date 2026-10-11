import tempfile
from electorn.execution.runner import CommandRunner
from electorn.verification.syntax_checker import SyntaxChecker
from electorn.verification.test_runner import TestRunner
from electorn.workspace.file_manager import FileManager
from electorn.workspace.permissions import PermissionManager


def test_syntax_checker_python_and_json():
    with tempfile.TemporaryDirectory() as tmp_dir:
        fm = FileManager(tmp_dir, permissions=PermissionManager(auto_approve=True))
        checker = SyntaxChecker(fm)

        # Valid python
        fm.write_file("valid.py", "def add(a, b):\n    return a + b\n")
        res1 = checker.check_file("valid.py")
        assert res1.is_valid is True

        # Invalid python syntax
        fm.write_file("invalid.py", "def add(a, b)\n    return a + b\n")
        res2 = checker.check_file("invalid.py")
        assert res2.is_valid is False
        assert "expected ':'" in res2.error_message or "line 1" in res2.error_message

        # Valid JSON
        fm.write_file("valid.json", '{"name": "electorn"}')
        assert checker.check_file("valid.json").is_valid is True

        # Invalid JSON
        fm.write_file("invalid.json", '{"name": "electorn"')
        assert checker.check_file("invalid.json").is_valid is False


def test_test_runner_discovery():
    with tempfile.TemporaryDirectory() as tmp_dir:
        fm = FileManager(tmp_dir, permissions=PermissionManager(auto_approve=True))
        runner = CommandRunner(tmp_dir)
        tr = TestRunner(fm, runner)

        # Initially no tests
        assert tr.discover_test_command() is None

        # Write test file
        fm.write_file("tests/test_demo.py", "def test_ok():\n    assert 1 == 1\n")
        cmd = tr.discover_test_command()
        assert cmd is not None and "pytest -q" in cmd

        # Execute tests
        res = tr.run_tests()
        assert res.passed is True
        assert res.passed_tests >= 1
