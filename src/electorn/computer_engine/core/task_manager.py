"""
Task Manager: Orchestrates end-to-end task execution, step verification, retries, and recovery.
"""

import time
from typing import Optional, List, Dict, Any

from electorn.computer_engine.types import (
    TaskPlan,
    TaskStep,
    ActionResult,
    ComputerState,
)
from electorn.computer_engine.core.action_planner import ActionPlanner
from electorn.computer_engine.core.action_executor import ActionExecutor
from electorn.computer_engine.core.action_validator import CoreActionValidator
from electorn.computer_engine.core.task_memory import TaskMemory
from electorn.computer_engine.perception.screen_analyzer import ScreenAnalyzer
from electorn.computer_engine.safety.emergency_stop import EmergencyStop


class TaskManager:
    def __init__(
        self,
        planner: Optional[ActionPlanner] = None,
        executor: Optional[ActionExecutor] = None,
        validator: Optional[CoreActionValidator] = None,
        memory: Optional[TaskMemory] = None,
        analyzer: Optional[ScreenAnalyzer] = None,
    ) -> None:
        self.planner = planner or ActionPlanner()
        self.executor = executor or ActionExecutor()
        self.validator = validator or CoreActionValidator()
        self.memory = memory or TaskMemory()
        self.analyzer = analyzer or ScreenAnalyzer()
        self.emergency_stop = EmergencyStop.get_instance()
        self.active_plan: Optional[TaskPlan] = None

    def execute_instruction(self, instruction: str) -> TaskPlan:
        """Execute natural language computer automation instruction."""
        # Check emergency stop
        if self.emergency_stop.check():
            plan = self.planner.plan_instruction(instruction)
            plan.status = "aborted"
            plan.error = "Emergency stop is active."
            return plan

        # 1. Perception: observe screen state
        current_state = self.analyzer.get_current_state()

        # 2. Plan
        plan = self.planner.plan_instruction(instruction, current_state)
        self.active_plan = plan
        plan.status = "running"

        # 3. Step-by-step execution
        for idx, step in enumerate(plan.steps):
            if self.emergency_stop.check():
                step.status = "aborted"
                step.error = "Aborted by emergency stop."
                plan.status = "aborted"
                break

            plan.current_step_index = idx
            step.status = "running"

            # Pre-validation
            pre_check = self.validator.validate_preconditions(step.action, current_state)
            if not pre_check.get("valid", True):
                step.status = "failed"
                step.error = pre_check.get("reason", "Precondition check failed.")
                plan.status = "failed"
                plan.error = step.error
                break

            # Physical execution with retry
            max_retries = 2
            step_result: Optional[ActionResult] = None

            for attempt in range(max_retries + 1):
                if self.emergency_stop.check():
                    break
                step.retry_count = attempt
                step_result = self.executor.execute(step.action)
                if step_result.success:
                    break
                time.sleep(0.5)

            step.result = step_result

            # Post-validation
            if step_result and step_result.success:
                step.status = "completed"
            else:
                step.status = "failed"
                step.error = step_result.error if step_result else "Execution failed."
                plan.status = "failed"
                plan.error = step.error
                break

        if plan.status == "running":
            plan.status = "completed"
            plan.completed_time = time.time()

        # 4. Record to persistent task memory
        self.memory.record_completed_task(plan)
        self.active_plan = None
        return plan
