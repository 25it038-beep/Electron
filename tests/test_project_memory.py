from pathlib import Path
from electorn.storage.project_memory import ProjectMemory


def test_project_memory_lifecycle(tmp_path: Path):
    ws = tmp_path / "workspace"
    ws.mkdir()

    mem = ProjectMemory(ws)
    assert mem.data.project_purpose == ""

    # Update memory
    mem.update(
        purpose="AI Student Portal",
        stack_updates={"backend": "FastAPI", "db": "SQLite"},
        decision="Use SQLite for lightweight zero-dependency deployment",
        completed_task="Designed schema",
    )

    # Verify context string
    ctx = mem.to_context_string()
    assert "[PROJECT MEMORY]" in ctx
    assert "AI Student Portal" in ctx
    assert "FastAPI" in ctx
    assert "SQLite" in ctx

    # Reload from disk
    mem2 = ProjectMemory(ws)
    assert mem2.data.project_purpose == "AI Student Portal"
    assert mem2.data.tech_stack["backend"] == "FastAPI"
    assert "Designed schema" in mem2.data.completed_tasks

    # Clear
    mem2.clear()
    assert mem2.data.project_purpose == ""
    assert not (ws / ".electorn" / "memory.json").exists()
