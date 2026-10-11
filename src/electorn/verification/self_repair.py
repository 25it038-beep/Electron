"""Automated self-repair loop: detects failures, applies fixes, and reruns tests."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Optional
from pydantic import BaseModel, Field
from electorn.verification.syntax_checker import SyntaxChecker
from electorn.verification.test_runner import TestRunner, TestRunResult
from electorn.workspace.file_manager import FileManager
from electorn.workspace.project_state import ProjectState

if TYPE_CHECKING:
    from electorn.agents.base import BaseAgent


class RepairAttempt(BaseModel):
    """Record of a self-repair attempt."""

    iteration: int
    error_summary: str
    files_modified: list[str] = Field(default_factory=list)
    success: bool = False
    details: Optional[str] = None


class SelfRepairEngine:
    """Orchestrates detection of errors and autonomous patching."""

    def __init__(
        self,
        file_manager: FileManager,
        syntax_checker: SyntaxChecker,
        test_runner: TestRunner,
        max_attempts: int = 3,
    ):
        self.file_manager = file_manager
        self.syntax_checker = syntax_checker
        self.test_runner = test_runner
        self.max_attempts = max_attempts

    def repair_syntax(
        self,
        repair_agent: "BaseAgent",
        state: ProjectState,
        failing_files: list[str],
        status_cb: Optional[Callable[[str], None]] = None,
    ) -> bool:
        """Iteratively fix static syntax errors in generated files."""
        for attempt in range(1, self.max_attempts + 1):
            bad_results = [
                self.syntax_checker.check_file(f)
                for f in failing_files
                if not self.syntax_checker.check_file(f).is_valid
            ]

            if not bad_results:
                if status_cb:
                    status_cb("✨ All syntax checks passed!")
                return True

            first_bad = bad_results[0]
            if status_cb:
                status_cb(
                    f"🔄 [Self-Repair Syntax {attempt}/{self.max_attempts}] Fixing {first_bad.file_path}: {first_bad.error_message}"
                )

            current_code = self.file_manager.read_file(first_bad.file_path)
            repair_prompt = f"""
Fix the syntax error in file '{first_bad.file_path}'.
Error details: {first_bad.error_message} (Line {first_bad.line_number or 'unknown'})

Current code:
```{Path(first_bad.file_path).suffix[1:]}
{current_code}
```

Return ONLY the full corrected code for '{first_bad.file_path}'.
Do not include conversational preamble.
"""
            fixed_code = repair_agent.execute_simple_code_repair(first_bad.file_path, repair_prompt)
            if fixed_code:
                self.file_manager.write_file(first_bad.file_path, fixed_code)

        return False

    def repair_test_failures(
        self,
        repair_agent: "BaseAgent",
        state: ProjectState,
        test_result: TestRunResult,
        status_cb: Optional[Callable[[str], None]] = None,
    ) -> bool:
        """Iteratively fix failing tests and application logic."""
        current_res = test_result
        for attempt in range(1, self.max_attempts + 1):
            if current_res.passed:
                if status_cb:
                    status_cb("✅ All automated tests passing!")
                return True

            if status_cb:
                status_cb(
                    f"🔄 [Self-Repair Tests {attempt}/{self.max_attempts}] Diagnosing test failures..."
                )

            # Extract failure output
            error_context = current_res.raw_output[-1500:]  # keep concise for small models

            repair_prompt = f"""
Automated tests failed!
Command run: {current_res.command}
Failure output:
{error_context}

Existing project files:
{state.get_file_summary()}

Analyze the failure output, determine which file(s) must be updated, and provide the complete fixed files.
"""
            patches = repair_agent.execute_multifixture_repair(repair_prompt, state)
            for file_path, content in patches.items():
                self.file_manager.write_file(file_path, content)
                state.mark_file_created(file_path)

            # Rerun tests
            current_res = self.test_runner.run_tests(current_res.command)

        return current_res.passed
