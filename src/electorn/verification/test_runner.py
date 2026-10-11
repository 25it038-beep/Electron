"""Automated discovery and execution of test suites."""

from __future__ import annotations

import re
import sys
from typing import Optional
from pydantic import BaseModel, Field
from electorn.execution.runner import CommandRunner, ExecutionResult
from electorn.workspace.file_manager import FileManager


class TestRunResult(BaseModel):
    """Structured results from a test run."""

    passed: bool
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    errors: list[str] = Field(default_factory=list)
    raw_output: str = ""
    command: str = ""


class TestRunner:
    """Discovers and runs automated test suites inside the workspace."""

    __test__ = False

    def __init__(self, file_manager: FileManager, runner: CommandRunner):
        self.file_manager = file_manager
        self.runner = runner

    def discover_test_command(self) -> Optional[str]:
        """Infer best test runner command based on project files."""
        files = self.file_manager.list_files()

        # Python test discovery
        has_python_tests = any(
            f.startswith("tests/") or f.endswith("_test.py") or f.startswith("test_")
            for f in files
        )
        if has_python_tests:
            return f'"{sys.executable}" -m pytest -q'

        # Node / JS test discovery
        if "package.json" in files:
            return "npm test"

        return None

    def run_tests(self, custom_command: Optional[str] = None) -> TestRunResult:
        """Run tests and return structured results."""
        discovered = self.discover_test_command()
        cmd = custom_command or discovered
        if cmd == "pytest" or cmd == "pytest -q":
            cmd = f'"{sys.executable}" -m pytest -q'
        if not cmd:
            return TestRunResult(
                passed=True,
                total_tests=0,
                passed_tests=0,
                failed_tests=0,
                raw_output="No test files or test runner discovered.",
                command="",
            )

        exec_res: ExecutionResult = self.runner.run(cmd, timeout=90, require_permission=False)
        output = f"{exec_res.stdout}\n{exec_res.stderr}".strip()

        # Pytest return code 5 means no tests were collected, which is not a failure for clean repos
        no_tests_collected = exec_res.returncode == 5 or "collected 0 items" in output or "no tests ran" in output
        passed = exec_res.is_success or no_tests_collected
        total = 0
        passed_count = 0
        failed_count = 0
        errors: list[str] = []

        # Pytest pattern matching: "3 passed, 1 failed in 0.12s" or "1 passed in 0.05s"
        pass_match = re.search(r"(\d+)\s+passed", output)
        fail_match = re.search(r"(\d+)\s+failed", output)
        err_match = re.search(r"(\d+)\s+error", output)

        if pass_match:
            passed_count = int(pass_match.group(1))
        if fail_match:
            failed_count += int(fail_match.group(1))
        if err_match:
            failed_count += int(err_match.group(1))

        total = passed_count + failed_count

        if not passed:
            # Capture failure lines
            for line in output.splitlines():
                if "FAILED" in line or "ERROR" in line or "SyntaxError" in line or "Traceback" in line:
                    errors.append(line.strip())

        return TestRunResult(
            passed=passed,
            total_tests=total,
            passed_tests=passed_count,
            failed_tests=failed_count,
            errors=errors[:10],  # Keep top errors to avoid context explosion
            raw_output=output,
            command=cmd,
        )
