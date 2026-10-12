"""Central Task Orchestration Manager coordinating Planner, Executor, Voice, and UI."""

from __future__ import annotations

import logging
import threading
from typing import Callable, Optional

from agent.action_schema import ExecutionResult, TaskPlan, TaskStep
from agent.executor import TaskExecutor
from agent.planner import TaskPlanner
from agent.task_state import TaskLifecycleState
from agent.tool_registry import ToolRegistry
from config.permissions import PermissionManager
from providers.base import BaseLLMProvider
from storage.database import TaskDatabase
from voice.text_to_speech import TextToSpeechEngine

logger = logging.getLogger(__name__)


class TaskManager:
    """Coordinates lifecycle transitions, async task workers, and real-time event notifications."""

    def __init__(
        self,
        planner: Optional[TaskPlanner] = None,
        executor: Optional[TaskExecutor] = None,
        tts: Optional[TextToSpeechEngine] = None,
    ) -> None:
        self.planner = planner or TaskPlanner()
        self.executor = executor or TaskExecutor()
        self.tts = tts
        self.current_state = TaskLifecycleState.IDLE
        self.current_plan: Optional[TaskPlan] = None
        self._worker_thread: Optional[threading.Thread] = None

        # Event callbacks
        self.on_state_change: Optional[Callable[[TaskLifecycleState], None]] = None
        self.on_plan_created: Optional[Callable[[TaskPlan], None]] = None
        self.on_step_update: Optional[Callable[[TaskStep], None]] = None
        self.on_task_finished: Optional[Callable[[ExecutionResult], None]] = None

    def _set_state(self, state: TaskLifecycleState) -> None:
        self.current_state = state
        if self.on_state_change:
            self.on_state_change(state)

    def submit_command(self, command: str, async_exec: bool = True) -> TaskPlan:
        """Process natural language command into an executable plan and launch execution."""
        self._set_state(TaskLifecycleState.UNDERSTAND)
        logger.info(f"Received user command: {command}")

        self._set_state(TaskLifecycleState.PLAN)
        plan = self.planner.plan(command)
        self.current_plan = plan

        if self.on_plan_created:
            self.on_plan_created(plan)

        if async_exec:
            self._worker_thread = threading.Thread(target=self._run_plan, args=(plan,), daemon=True)
            self._worker_thread.start()
        else:
            self._run_plan(plan)

        return plan

    def _run_plan(self, plan: TaskPlan) -> None:
        self._set_state(TaskLifecycleState.EXECUTE)

        def step_start_cb(step: TaskStep) -> None:
            if self.on_step_update:
                self.on_step_update(step)

        def step_complete_cb(step: TaskStep) -> None:
            if self.on_step_update:
                self.on_step_update(step)

        result = self.executor.execute_plan(
            plan=plan,
            on_step_start=step_start_cb,
            on_step_complete=step_complete_cb,
        )

        if result.success:
            self._set_state(TaskLifecycleState.REPORT)
        else:
            self._set_state(TaskLifecycleState.FAILED)

        # Voice feedback
        if self.tts and result.spoken_summary:
            try:
                self.tts.speak(result.spoken_summary, async_mode=True)
            except Exception as e:
                logger.error(f"TTS feedback error: {e}")

        if self.on_task_finished:
            self.on_task_finished(result)

        self._set_state(TaskLifecycleState.IDLE)

    def cancel_current_task(self) -> None:
        """Cancel currently executing task immediately."""
        self.executor.cancel()
        if self.tts:
            self.tts.stop()
        self._set_state(TaskLifecycleState.IDLE)

    def pause_current_task(self) -> None:
        self.executor.pause()
        self._set_state(TaskLifecycleState.PAUSED)

    def resume_current_task(self) -> None:
        self.executor.resume()
        self._set_state(TaskLifecycleState.EXECUTE)
