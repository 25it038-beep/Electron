"""Sequential task execution engine with verification, security enforcement, and recovery."""

from __future__ import annotations

import logging
import time
from typing import Callable, Optional

from agent.action_schema import ExecutionResult, TaskPlan, TaskStep
from agent.recovery import RecoveryStrategy
from agent.tool_registry import ToolRegistry
from agent.verification import ActionVerifier
from config.permissions import PermissionLevel, PermissionManager
from storage.database import TaskDatabase

logger = logging.getLogger(__name__)


class TaskExecutor:
    """Executes TaskPlan steps sequentially with security confirmation and deterministic verification."""

    def __init__(
        self,
        tool_registry: Optional[ToolRegistry] = None,
        permission_engine: Optional[PermissionManager] = None,
        database: Optional[TaskDatabase] = None,
        confirm_callback: Optional[Callable[[TaskStep], bool]] = None,
    ) -> None:
        self.registry = tool_registry or ToolRegistry()
        self.permissions = permission_engine or PermissionManager()
        self.db = database or TaskDatabase()
        self.verifier = ActionVerifier(browser_engine=self.registry.browser_engine)
        self.recovery = RecoveryStrategy(max_retries=2)
        self.confirm_callback = confirm_callback  # GUI hook for Level 2 confirmation
        self.is_cancelled = False
        self.is_paused = False

    def execute_plan(
        self,
        plan: TaskPlan,
        on_step_start: Optional[Callable[[TaskStep], None]] = None,
        on_step_complete: Optional[Callable[[TaskStep], None]] = None,
    ) -> ExecutionResult:
        """Execute all steps in a plan sequentially."""
        start_time = time.time()
        plan.status = "running"
        self.is_cancelled = False
        self.is_paused = False

        # Persist task start to database
        self.db.save_task(
            task_id=plan.task_id,
            transcript=plan.original_transcript,
            status="running",
            total_steps=len(plan.steps),
        )

        completed_count = 0
        all_verified = True
        final_error: Optional[str] = None

        for idx, step in enumerate(plan.steps):
            if self.is_cancelled:
                plan.status = "cancelled"
                self.db.update_task_status(plan.task_id, "cancelled", error_msg="Task cancelled by user.")
                return ExecutionResult(
                    task_id=plan.task_id,
                    success=False,
                    message="Task was cancelled by user.",
                    spoken_summary="Task cancelled.",
                    steps_completed=completed_count,
                    total_steps=len(plan.steps),
                    duration_sec=time.time() - start_time,
                    error="Cancelled",
                )

            # Wait if paused
            while self.is_paused and not self.is_cancelled:
                time.sleep(0.2)

            plan.current_step_index = idx
            step.status = "in_progress"
            step_start = time.time()

            if on_step_start:
                on_step_start(step)

            # 1. Security Check
            risk_level = self.permissions.check_action(step.action, step.parameters)
            if risk_level == PermissionLevel.LEVEL_3_RESTRICTED:
                step.status = "failed"
                step.error = f"Security Policy Violation: Action '{step.action}' is restricted."
                plan.status = "failed"
                self._record_step(plan.task_id, step, int((time.time() - step_start) * 1000))
                return self._build_result(plan, False, step.error, completed_count, start_time)

            if risk_level == PermissionLevel.LEVEL_2_CONFIRM:
                confirmed = True
                if self.confirm_callback:
                    confirmed = self.confirm_callback(step)
                if not confirmed:
                    step.status = "skipped"
                    step.error = "User declined confirmation."
                    plan.status = "cancelled"
                    self._record_step(plan.task_id, step, int((time.time() - step_start) * 1000))
                    return self._build_result(plan, False, "Action cancelled by user confirmation prompt.", completed_count, start_time)

            # 2. Execution
            res = self.registry.execute_tool(step.action, step.parameters)

            # 3. Recovery if step failed
            if not res.get("success", False):
                res = self.recovery.attempt_recovery(
                    step.action,
                    step.parameters,
                    res.get("message", "Unknown error"),
                    self.registry.execute_tool,
                )

            step_duration_ms = int((time.time() - step_start) * 1000)
            step.duration_ms = step_duration_ms
            step.result = res.get("message", "")

            # 4. Post-Step Verification
            if res.get("success", False):
                verified, evidence = self.verifier.verify_step(step.action, step.parameters, res)
                step.verification_evidence = evidence
                if verified:
                    step.status = "completed"
                    completed_count += 1
                else:
                    step.status = "failed"
                    step.error = f"Step executed but failed verification: {evidence}"
                    all_verified = False
                    final_error = step.error
                    self._record_step(plan.task_id, step, step_duration_ms)
                    if on_step_complete:
                        on_step_complete(step)
                    break
            else:
                step.status = "failed"
                step.error = res.get("message", "Execution failed")
                final_error = step.error
                self._record_step(plan.task_id, step, step_duration_ms)
                if on_step_complete:
                    on_step_complete(step)
                break

            self._record_step(plan.task_id, step, step_duration_ms)
            if on_step_complete:
                on_step_complete(step)

        # Final outcome
        duration = time.time() - start_time
        success = (completed_count == len(plan.steps)) and all_verified
        plan.status = "completed" if success else "failed"

        self.db.update_task_status(
            plan.task_id,
            plan.status,
            completed_steps=completed_count,
            error_msg=final_error,
        )

        msg = "All steps executed and verified successfully." if success else f"Workflow failed: {final_error}"
        spoken = f"Task completed successfully. {completed_count} actions verified." if success else f"Task encountered an issue: {final_error}"

        return ExecutionResult(
            task_id=plan.task_id,
            success=success,
            message=msg,
            spoken_summary=spoken,
            steps_completed=completed_count,
            total_steps=len(plan.steps),
            duration_sec=duration,
            error=final_error,
            verification_passed=all_verified,
        )

    def cancel(self) -> None:
        """Signal current plan execution to cancel immediately."""
        self.is_cancelled = True

    def pause(self) -> None:
        """Pause step loop."""
        self.is_paused = True

    def resume(self) -> None:
        """Resume step loop."""
        self.is_paused = False

    def _record_step(self, task_id: str, step: TaskStep, duration_ms: int) -> None:
        self.db.save_step(
            task_id=task_id,
            step_id=step.step_id,
            action=step.action,
            parameters=step.parameters,
            status=step.status,
            result=step.result,
            evidence=step.verification_evidence,
            duration_ms=duration_ms,
            error=step.error,
        )

    def _build_result(self, plan: TaskPlan, success: bool, msg: str, completed: int, start_time: float) -> ExecutionResult:
        return ExecutionResult(
            task_id=plan.task_id,
            success=success,
            message=msg,
            spoken_summary=f"Task aborted: {msg}",
            steps_completed=completed,
            total_steps=len(plan.steps),
            duration_sec=time.time() - start_time,
            error=msg,
            verification_passed=False,
        )
