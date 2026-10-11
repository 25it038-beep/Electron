"""Autonomous task planning and execution engine with explicit states and real terminal progress."""

from __future__ import annotations

from enum import Enum
from typing import Callable, Optional
from pydantic import BaseModel, Field


class TaskState(str, Enum):
    """Explicit lifecycle states for autonomous tasks."""

    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"
    CANCELLED = "CANCELLED"


class Task(BaseModel):
    """Verifiable step in an autonomous development plan."""

    id: str
    description: str
    dependencies: list[str] = Field(default_factory=list)
    status: TaskState = TaskState.PENDING
    files_affected: list[str] = Field(default_factory=list)
    validation_requirements: list[str] = Field(default_factory=list)
    error_details: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    result: Optional[str] = None

    @property
    def status_badge(self) -> str:
        """Formatted terminal badge matching the required execution format."""
        if self.status == TaskState.COMPLETED:
            return "[PASS]"
        elif self.status == TaskState.IN_PROGRESS:
            return "[RUN ]"
        elif self.status == TaskState.PENDING:
            return "[WAIT]"
        elif self.status == TaskState.FAILED:
            return "[FAIL]"
        elif self.status == TaskState.BLOCKED:
            return "[BLCK]"
        elif self.status == TaskState.CANCELLED:
            return "[CANC]"
        return "[????]"


class TaskPlan(BaseModel):
    """Complete structured task plan for an application build."""

    project_name: str
    tasks: list[Task] = Field(default_factory=list)
    is_cancelled: bool = False

    def get_task(self, task_id: str) -> Optional[Task]:
        """Lookup task by ID."""
        for t in self.tasks:
            if t.id == task_id:
                return t
        return None

    def add_task(
        self,
        id: str,
        description: str,
        dependencies: Optional[list[str]] = None,
        files_affected: Optional[list[str]] = None,
        validation_requirements: Optional[list[str]] = None,
    ) -> Task:
        """Add a new task to the plan."""
        t = Task(
            id=id,
            description=description,
            dependencies=dependencies or [],
            files_affected=files_affected or [],
            validation_requirements=validation_requirements or [],
        )
        self.tasks.append(t)
        return t

    def get_next_runnable_task(self) -> Optional[Task]:
        """Find the next PENDING task whose dependencies have all COMPLETED."""
        if self.is_cancelled:
            return None

        completed_ids = {t.id for t in self.tasks if t.status == TaskState.COMPLETED}
        failed_ids = {t.id for t in self.tasks if t.status in (TaskState.FAILED, TaskState.CANCELLED)}

        for task in self.tasks:
            if task.status == TaskState.PENDING:
                # If any dependency failed, mark this task blocked
                if any(dep in failed_ids for dep in task.dependencies):
                    task.status = TaskState.BLOCKED
                    continue

                # All dependencies satisfied
                if all(dep in completed_ids for dep in task.dependencies):
                    return task

        return None

    def render_progress_table(self) -> str:
        """Render the explicit text terminal progress."""
        lines = [
            "ELECTORN DEVELOPMENT AGENT",
            f"Project: {self.project_name}",
            "",
        ]
        for t in self.tasks:
            files_str = f" ({', '.join(t.files_affected[:2])})" if t.files_affected else ""
            lines.append(f"{t.status_badge} {t.description}{files_str}")
        return "\n".join(lines)


class TaskPlanner:
    """Creates and tracks structured execution tasks for application builds."""

    @staticmethod
    def create_standard_plan(project_name: str, prompt: str, categories: list[str]) -> TaskPlan:
        """Construct structured tasks with explicit dependencies and validations."""
        plan = TaskPlan(project_name=project_name)

        # 1. Requirements analysis
        plan.add_task(
            id="req_analysis",
            description="Requirements analyzed",
            validation_requirements=["User specifications and tech stack resolved"],
        )

        # 2. Project structure created
        plan.add_task(
            id="proj_structure",
            description="Project structure created",
            dependencies=["req_analysis"],
            validation_requirements=["Directory tree and manifests generated"],
        )

        # 3. Data models / Database
        if "database" in categories or "backend" in categories:
            plan.add_task(
                id="database_gen",
                description="Database & persistence layer generated",
                dependencies=["proj_structure"],
                validation_requirements=["Models and schemas syntactically valid"],
            )

        # 4. Backend services
        if "backend" in categories or "api" in categories:
            plan.add_task(
                id="backend_gen",
                description="Backend API and services generated",
                dependencies=["database_gen" if "database" in categories else "proj_structure"],
                validation_requirements=["Endpoints, models, and business logic complete"],
            )

        # 5. Frontend UI
        if "frontend" in categories or "ui" in categories or "website" in categories:
            plan.add_task(
                id="frontend_gen",
                description="Frontend UI and styling generated",
                dependencies=["backend_gen" if "backend" in categories else "proj_structure"],
                validation_requirements=["Interactive UI, client templates, and styles functional"],
            )

        # 6. Automated tests
        prev_dep = "frontend_gen" if ("frontend" in categories or "ui" in categories) else "backend_gen"
        if prev_dep not in [t.id for t in plan.tasks]:
            prev_dep = "proj_structure"

        plan.add_task(
            id="test_suite_gen",
            description="Automated test suite generated",
            dependencies=[prev_dep],
            validation_requirements=["Test cases cover happy path and error handling"],
        )

        # 7. Dependency and configuration validation
        plan.add_task(
            id="dep_validation",
            description="Dependency and configuration validation",
            dependencies=["test_suite_gen"],
            validation_requirements=["requirements.txt/package.json and README complete"],
        )

        # 8. Verification and Self-Repair
        plan.add_task(
            id="verification",
            description="Code verification & quality assurance",
            dependencies=["dep_validation"],
            validation_requirements=["Syntax checks passing, unit test suite executed"],
        )

        return plan
