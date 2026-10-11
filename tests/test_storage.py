import tempfile
from pathlib import Path
from electorn.storage.config import Config, load_config, save_config
from electorn.storage.history import SessionHistory


def test_config_defaults_and_serialization():
    cfg = Config()
    assert cfg.runtime.ollama_base_url == "http://localhost:11434"
    assert cfg.orchestration.sequential_execution is True
    assert cfg.orchestration.max_repair_attempts == 3

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir) / ".electorn.yaml"
        save_config(cfg, tmp_path)
        assert tmp_path.exists()

        loaded = load_config(tmp_dir)
        assert loaded.runtime.ollama_base_url == cfg.runtime.ollama_base_url
        assert loaded.orchestration.sequential_execution is True


def test_session_history_logging():
    with tempfile.TemporaryDirectory() as tmp_dir:
        history = SessionHistory(
            session_id="test-session-123",
            prompt="Build a job recommendation engine",
            model_used="llama3.2:latest",
        )
        action = history.record_action(
            agent_name="Architect",
            role="Lead Architect",
            action_type="plan",
            summary="Created system architecture",
            files_affected=["main.py"],
        )
        assert action.agent_name == "Architect"
        assert len(history.actions) == 1

        saved_path = history.save(tmp_dir)
        assert saved_path.exists()
        assert "test-session-123.json" in str(saved_path)
