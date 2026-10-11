import sys
import tempfile
from electorn.execution.environment import EnvironmentDetector
from electorn.execution.runner import CommandRunner
from electorn.workspace.permissions import PermissionManager


def test_environment_detector():
    env = EnvironmentDetector.detect()
    assert env.python_version != ""
    assert env.os_system != ""


def test_command_runner():
    with tempfile.TemporaryDirectory() as tmp_dir:
        runner = CommandRunner(tmp_dir, permissions=PermissionManager(auto_approve=True))
        # Run simple Python command using active interpreter
        cmd = f'"{sys.executable}" -c "print(123 + 456)"'
        res = runner.run(cmd)
        assert res.is_success is True
        assert "579" in res.stdout
        assert res.returncode == 0


def test_command_runner_permission_rejection():
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Prompt function that rejects
        runner = CommandRunner(tmp_dir, permissions=PermissionManager(auto_approve=False, prompt_fn=lambda _: False))
        cmd = f'"{sys.executable}" -c "print(1)"'
        res = runner.run(cmd)
        assert res.permitted is False
        assert res.is_success is False
