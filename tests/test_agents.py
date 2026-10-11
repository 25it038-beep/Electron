from electorn.agents.architect import ArchitectAgent
from electorn.agents.base import BaseAgent
from electorn.runtime.model_selector import ModelProfile
from electorn.runtime.ollama_client import OllamaClient


def test_base_agent_file_extraction_markdown():
    text = """
Here are the files you requested:

FILE: src/hello.py
```python
def hello():
    print("hello from electorn")
```

FILE: config.json
```json
{
  "active": true
}
```
"""
    files = BaseAgent.extract_files_from_text(text)
    assert "src/hello.py" in files
    assert 'print("hello from electorn")' in files["src/hello.py"]
    assert "config.json" in files
    assert '"active": true' in files["config.json"]


def test_base_agent_file_extraction_json():
    text = """
{
  "summary": "Generated architecture files",
  "files": [
    {
      "path": "app.py",
      "content": "print('App running')"
    }
  ]
}
"""
    files = BaseAgent.extract_files_from_text(text)
    assert "app.py" in files
    assert "print('App running')" in files["app.py"]


def test_architect_agent_mock():
    client = OllamaClient(mock_mode=True)
    profile = ModelProfile(
        name="llama3.2:latest",
        tier="small",
        parameter_approx=3.0,
        recommended_context=4096,
        is_code_specialized=True,
        description="Small model",
    )
    architect = ArchitectAgent(client, profile)
    spec = architect.design_system("Build a job recommendation engine")
    assert spec.project_name != ""
    assert spec.run_command != ""
    assert len(spec.file_manifest) > 0


def test_base_agent_stream_ask():
    client = OllamaClient(mock_mode=True)
    profile = ModelProfile(
        name="llama3.2:latest",
        tier="small",
        parameter_approx=3.0,
        recommended_context=4096,
        is_code_specialized=True,
        description="Small model",
    )
    agent = BaseAgent(
        name="Tester",
        role="Tester Agent",
        icon="🧪",
        system_prompt="Test prompt",
        client=client,
        model_profile=profile,
    )
    tokens = list(agent.stream_ask("Hello"))
    assert len(tokens) > 0
    assert "Mock streaming response chunk" in tokens[0]
