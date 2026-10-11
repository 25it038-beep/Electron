import tempfile
from electorn.orchestration.team import MultiAgentTeam
from electorn.orchestration.application_builder import ApplicationBuilder


def test_application_builder_mock_execution():
    with tempfile.TemporaryDirectory() as tmp_dir:
        team = MultiAgentTeam(
            workspace_dir=tmp_dir,
            auto_approve=True,
            mock_mode=True,
        )

        builder = ApplicationBuilder(team)
        result = builder.build(
            prompt="Build a full stack FastAPI service with SQLite database",
            install_dependencies=False,
            launch_preview=False,
        )

        assert result is not None
        assert result.project_name != ""
        assert len(result.files_created) > 0
        assert result.final_status in ("READY FOR REVIEW", "PASS WITH WARNINGS")
        assert (team.workspace_dir / "app.py").exists() or (team.workspace_dir / "main.py").exists() or len(team.file_manager.list_files()) > 0
