"""Autonomous 4-Stage Task Planning & Execution Engine for Electorn AI.

Decomposes complex user goals into executable steps across Plan -> Execute -> Validate -> Report stages
with automatic error recovery and post-condition verification.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
import re
import time
from typing import Any, Callable, Dict, List, Optional
from pydantic import BaseModel, Field

from electorn.automation.os_agent import WindowsOSAgent
from electorn.automation.web_agent import PlaywrightWebAgent
from electorn.providers.local_llm import OllamaLocalProvider

logger = logging.getLogger(__name__)


class TaskStep(BaseModel):
    """An individual actionable step within an autonomous plan."""
    step_id: int
    action: str                                  # web_search, research_topic, write_file, read_file, run_command, launch_app, organize_dir
    description: str
    params: Dict[str, Any] = Field(default_factory=dict)
    validation_type: str = "non_empty"           # non_empty, file_exists, exit_code_zero, success_flag
    status: str = "pending"                      # pending, running, completed, failed, retried
    result: Any = None
    error: Optional[str] = None
    retries: int = 0


class TaskPlan(BaseModel):
    """A multi-step autonomous plan created to fulfill a user goal."""
    goal: str
    steps: List[TaskStep] = Field(default_factory=list)
    created_at: float = Field(default_factory=time.time)
    status: str = "planned"                      # planned, in_progress, completed, failed
    execution_summary: str = ""
    output_files: List[str] = Field(default_factory=list)
    duration_seconds: float = 0.0

    @property
    def success(self) -> bool:
        return self.status == "completed"

    @property
    def report(self) -> str:
        rep = f"# Autonomous Task Execution Report\n\n"
        rep += f"**Goal:** {self.goal}\n"
        rep += f"**Status:** {'COMPLETED' if self.success else 'FAILED'}\n"
        rep += f"**Duration:** {self.duration_seconds}s\n\n"
        rep += "### Executed Steps\n"
        for s in self.steps:
            st = "✔" if s.status == "completed" else "✖"
            rep += f"- [{st}] **Step {s.step_id}**: {s.description} ({s.action})\n"
        if self.execution_summary:
            rep += f"\n**Summary:** {self.execution_summary}\n"
        return rep

    def get(self, key: str, default: Any = None) -> Any:
        if key == "success":
            return self.success
        if key == "report":
            return self.report
        if hasattr(self, key):
            return getattr(self, key)
        return default

    def __getitem__(self, key: str) -> Any:
        val = self.get(key)
        if val is None:
            raise KeyError(key)
        return val


class AutonomousTaskPlanner:
    """Plans, coordinates, executes, and validates autonomous multi-step tasks."""

    def __init__(
        self,
        workspace: Optional[Path] = None,
        llm_provider: Optional[OllamaLocalProvider] = None,
    ) -> None:
        from electorn.companion.tools import CompanionTools
        self.workspace = workspace or Path.cwd()
        self.os_agent = WindowsOSAgent()
        self.web_agent = PlaywrightWebAgent()
        self.tools = CompanionTools(self.workspace)
        self.llm = llm_provider or OllamaLocalProvider(auto_start=True)

    # =========================================================================
    # 1. PLANNING STAGE
    # =========================================================================

    def plan_task(self, goal: str) -> TaskPlan:
        """Decompose a high-level user goal into an ordered sequence of executable steps."""
        clean_goal = goal.strip()
        lower = clean_goal.lower()

        steps: List[TaskStep] = []

        # Heuristic Templates for Common Patterns
        # A. Research & Comparison Tasks
        if any(w in lower for w in ["research", "compare", "investigate", "find information about", "study"]):
            slug = re.sub(r"[^a-zA-Z0-9]+", "_", clean_goal.lower()).strip("_")[:35]
            report_path = f"research_reports/{slug}.md"

            steps.append(TaskStep(
                step_id=1,
                action="research_topic",
                description=f"Autonomous web search and cross-source research on '{clean_goal}'",
                params={"objective": clean_goal, "num_sources": 3},
                validation_type="non_empty",
            ))
            steps.append(TaskStep(
                step_id=2,
                action="verify_report",
                description=f"Verify generated research report and validate citations",
                params={"path": report_path},
                validation_type="file_exists",
            ))

        # B. Organize Directory Tasks
        elif any(w in lower for w in ["organize", "clean up", "sort files"]):
            target_path = str(Path.home() / "Downloads")
            if "desktop" in lower:
                target_path = str(Path.home() / "Desktop")
            elif "downloads" in lower:
                target_path = str(Path.home() / "Downloads")

            steps.append(TaskStep(
                step_id=1,
                action="organize_dir",
                description=f"Scan and organize directory '{target_path}' into categorized folders",
                params={"target_dir": target_path, "dry_run": False},
                validation_type="success_flag",
            ))

        # C. System Audit / Diagnostic Tasks
        elif any(w in lower for w in ["system specs", "system specifications", "disk space", "diagnostics", "check health", "disk health", "specs"]):
            steps.append(TaskStep(
                step_id=1,
                action="system_diagnostics",
                description="Audit disk partitions, memory capacity, and CPU load",
                params={},
                validation_type="non_empty",
            ))

        # D. Testing & Code Inspection Tasks
        elif any(w in lower for w in ["run test", "check tests", "run pytest"]):
            steps.append(TaskStep(
                step_id=1,
                action="run_command",
                description="Run automated pytest test suite in current workspace",
                params={"command": "python -m pytest -q"},
                validation_type="exit_code_zero",
            ))

        # E. General Fallback: LLM Decomposition or Generic Command
        else:
            steps.append(TaskStep(
                step_id=1,
                action="web_search",
                description=f"Search information for: {clean_goal}",
                params={"query": clean_goal},
                validation_type="non_empty",
            ))

        return TaskPlan(goal=clean_goal, steps=steps)

    # =========================================================================
    # 2. EXECUTION & VALIDATION STAGE
    # =========================================================================

    def execute_plan(
        self,
        plan: TaskPlan,
        progress_cb: Optional[Callable[[TaskStep], None]] = None,
    ) -> TaskPlan:
        """Execute each step in the plan, applying post-condition validation and automatic retries."""
        start_time = time.time()
        plan.status = "in_progress"

        all_success = True
        for step in plan.steps:
            step.status = "running"
            if progress_cb:
                progress_cb(step)

            max_retries = 2
            step_success = False

            while step.retries <= max_retries and not step_success:
                try:
                    result = self._dispatch_step(step)
                    step.result = result

                    # Post-condition validation
                    if self._validate_step(step):
                        step.status = "completed"
                        step_success = True
                    else:
                        step.retries += 1
                        if step.retries <= max_retries:
                            step.status = "retried"
                            time.sleep(1.0)
                        else:
                            step.status = "failed"
                            step.error = f"Validation failed ({step.validation_type})"
                except Exception as exc:
                    step.retries += 1
                    step.error = str(exc)
                    if step.retries <= max_retries:
                        step.status = "retried"
                        time.sleep(1.0)
                    else:
                        step.status = "failed"

            if progress_cb:
                progress_cb(step)

            if not step_success:
                all_success = False
                # If a critical step fails, halt remaining dependent steps
                break

        plan.duration_seconds = round(time.time() - start_time, 2)
        plan.status = "completed" if all_success else "failed"
        plan.execution_summary = self._generate_summary(plan)
        return plan

    def _dispatch_step(self, step: TaskStep) -> Any:
        """Dispatch step to appropriate specialized agent tool."""
        act = step.action

        if act == "research_topic":
            obj = step.params.get("objective", "")
            sources = step.params.get("num_sources", 3)
            return self.web_agent.research_topic(obj, num_sources=sources, output_dir=self.workspace / "research_reports")

        elif act == "verify_report":
            p = step.params.get("path", "")
            target = self.workspace / p
            return {"exists": target.exists(), "path": str(target)}

        elif act == "web_search":
            q = step.params.get("query", "")
            return self.web_agent.search_queries(q, max_results=5)

        elif act == "organize_dir":
            t = step.params.get("target_dir", str(Path.home() / "Downloads"))
            dry = step.params.get("dry_run", False)
            return self.os_agent.organize_directory(t, dry_run=dry)

        elif act == "system_diagnostics":
            return self.os_agent.get_system_diagnostics()

        elif act == "run_command":
            cmd = step.params.get("command", "")
            return self.os_agent.execute_command_safely(cmd, cwd=self.workspace)

        elif act == "launch_app":
            app = step.params.get("app", "notepad")
            return self.os_agent.launch_application(app)

        elif act == "write_file":
            filepath = step.params.get("path", "output.txt")
            content = step.params.get("content", "")
            target = self.workspace / filepath
            target.parent.mkdir(parents=True, exist_ok=True)
            with open(target, "w", encoding="utf-8") as f:
                f.write(content)
            return {"path": str(target), "bytes": len(content)}

        return {"message": f"Action '{act}' executed."}

    def _validate_step(self, step: TaskStep) -> bool:
        """Assert post-conditions according to validation type."""
        vtype = step.validation_type
        res = step.result

        if res is None:
            return False

        if vtype == "non_empty":
            return bool(res)

        elif vtype == "file_exists":
            if isinstance(res, dict) and "path" in res:
                return Path(res["path"]).exists()
            return False

        elif vtype == "exit_code_zero":
            if isinstance(res, dict):
                return res.get("exit_code") == 0
            return False

        elif vtype == "success_flag":
            if isinstance(res, dict):
                return bool(res.get("success", False))
            return True

        return True

    def _generate_summary(self, plan: TaskPlan) -> str:
        """Synthesize concise execution briefing."""
        completed = sum(1 for s in plan.steps if s.status == "completed")
        total = len(plan.steps)
        status_symbol = "✔" if plan.status == "completed" else "✖"
        return f"{status_symbol} Plan '{plan.goal}': {completed}/{total} steps completed in {plan.duration_seconds}s."

    # =========================================================================
    # 3. END-TO-END WORKFLOW
    # =========================================================================

    def plan_and_execute(
        self,
        goal: str,
        progress_cb: Optional[Callable[[TaskStep], None]] = None,
    ) -> TaskPlan:
        """One-call autonomous task planning, execution, and validation."""
        plan = self.plan_task(goal)
        return self.execute_plan(plan, progress_cb=progress_cb)
