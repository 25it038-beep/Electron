import tempfile
from electorn.orchestration.team import MultiAgentTeam
from electorn.storage.config import Config


def test_multi_agent_team_mock_lifecycle():
    with tempfile.TemporaryDirectory() as tmp_dir:
        team = MultiAgentTeam(
            workspace_dir=tmp_dir,
            auto_approve=True,
            mock_mode=True,
        )

        assert team.architect.name == "Architect"
        assert team.database.name == "Database Engineer"
        assert team.backend.name == "Backend Developer"
        assert team.frontend.name == "Frontend Developer"
        assert team.integration.name == "Integration Specialist"
        assert team.qa_tester.name == "QA Engineer"
        assert team.devops.name == "DevOps Engineer"

        # Run pipeline in mock mode
        state = team.develop("Build a job recommendation platform")
        assert state is not None
        assert state.specification is not None

        # Verify files were written
        files = team.file_manager.list_files()
        assert len(files) > 0
        assert "app.py" in files
