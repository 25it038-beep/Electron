"""Unit tests for AutonomousTaskPlanner (Plan -> Execute -> Validate -> Report)."""

import tempfile
from pathlib import Path
import pytest

from electorn.planner.task_planner import (
    AutonomousTaskPlanner,
    TaskPlan,
    TaskStep,
)


def test_task_plan_structure():
    planner = AutonomousTaskPlanner()
    plan = planner.plan_task("Audit and organize temp directory")
    assert isinstance(plan, TaskPlan)
    assert plan.goal == "Audit and organize temp directory"
    assert len(plan.steps) > 0
    assert plan.steps[0].action != ""


def test_validation_rule_checks():
    planner = AutonomousTaskPlanner()

    # Rule: non_empty
    step1 = TaskStep(step_id=1, action="test", description="t", validation_type="non_empty", result="some content")
    assert planner._validate_step(step1) is True

    step1_empty = TaskStep(step_id=1, action="test", description="t", validation_type="non_empty", result="")
    assert planner._validate_step(step1_empty) is False

    # Rule: exit_code_zero
    step2 = TaskStep(step_id=2, action="test", description="t", validation_type="exit_code_zero", result={"exit_code": 0})
    assert planner._validate_step(step2) is True

    step2_fail = TaskStep(step_id=2, action="test", description="t", validation_type="exit_code_zero", result={"exit_code": 1})
    assert planner._validate_step(step2_fail) is False

    # Rule: success_flag
    step3 = TaskStep(step_id=3, action="test", description="t", validation_type="success_flag", result={"success": True})
    assert planner._validate_step(step3) is True

    step3_fail = TaskStep(step_id=3, action="test", description="t", validation_type="success_flag", result={"success": False})
    assert planner._validate_step(step3_fail) is False


def test_planner_execution_pipeline():
    with tempfile.TemporaryDirectory() as tmp_dir:
        planner = AutonomousTaskPlanner(workspace=Path(tmp_dir))
        result = planner.plan_and_execute("Check system specifications and disk health")
        assert result.success is True or result.status in ("completed", "planned")
        assert "Autonomous Task Execution Report" in result.report
        assert len(result.steps) > 0
