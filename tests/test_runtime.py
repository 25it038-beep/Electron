from electorn.runtime.model_selector import ModelSelector
from electorn.runtime.ollama_client import OllamaClient, OllamaModelInfo, OllamaResponse


def test_ollama_response_json_parsing():
    # Test raw json
    resp1 = OllamaResponse(content='{"name": "electorn", "status": "ok"}', model="test")
    assert resp1.parse_json() == {"name": "electorn", "status": "ok"}

    # Test markdown enclosed json
    resp2 = OllamaResponse(
        content='Here is the result:\n```json\n{"action": "create", "file": "app.py"}\n```\nHope this helps!',
        model="test",
    )
    assert resp2.parse_json() == {"action": "create", "file": "app.py"}

    # Test conversational small-model output with extra brackets
    resp3 = OllamaResponse(
        content='Sure, I generated the following config: {"key": "value"} thanks.',
        model="test",
    )
    assert resp3.parse_json() == {"key": "value"}


def test_model_selector_heuristics():
    client = OllamaClient(mock_mode=True)
    selector = ModelSelector(client)

    small_info = OllamaModelInfo(name="llama3.2:1b", size_bytes=1_200_000_000)
    profile_small = selector.profile_model(small_info)
    assert profile_small.tier == "small"
    assert profile_small.parameter_approx == 1.0

    coder_info = OllamaModelInfo(name="qwen2.5-coder:7b", size_bytes=4_500_000_000)
    profile_coder = selector.profile_model(coder_info)
    assert profile_coder.is_code_specialized is True
    assert profile_coder.tier == "medium"

    best = selector.select_best_model()
    assert best is not None
    assert best.name in ["llama3.2:latest", "qwen3-vl:4b-instruct"]
