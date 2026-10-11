from electorn.orchestration.planner import TaskPlan, TaskPlanner, TaskState


def test_task_planner_dependency_flow():
    plan = TaskPlanner.create_standard_plan(
        project_name="job-portal",
        prompt="Build a job portal with backend and frontend",
        categories=["backend", "frontend", "database"],
    )

    assert plan.project_name == "job-portal"
    assert len(plan.tasks) > 0

    # First runnable task should be req_analysis
    first = plan.get_next_runnable_task()
    assert first is not None
    assert first.id == "req_analysis"
    assert first.status_badge == "[WAIT]"

    # Mark first completed
    first.status = TaskState.COMPLETED
    assert first.status_badge == "[PASS]"

    # Next should be proj_structure
    second = plan.get_next_runnable_task()
    assert second is not None
    assert second.id == "proj_structure"

    # Progress table rendering
    table_str = plan.render_progress_table()
    assert "ELECTORN DEVELOPMENT AGENT" in table_str
    assert "[PASS] Requirements analyzed" in table_str
