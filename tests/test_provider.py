from electorn.runtime.ollama_client import OllamaClient
from electorn.runtime.provider import AutoProvider, CloudProvider, OllamaProvider, ProviderResponse


def test_provider_response_json():
    pr = ProviderResponse(content='{"status": "ok", "items": [1, 2]}', model="test", provider_name="test")
    assert pr.parse_json() == {"status": "ok", "items": [1, 2]}


def test_ollama_provider_mock():
    client = OllamaClient(mock_mode=True)
    provider = OllamaProvider(client=client, model_name="llama3.2:1b")

    assert provider.is_available() is True
    assert provider.get_model_name() == "llama3.2:1b"

    resp = provider.generate("hello")
    assert resp.content != ""
    assert resp.provider_name == "ollama (local)"


def test_cloud_provider_offline_check():
    cloud = CloudProvider(api_key="")
    assert cloud.is_available() is False

    # AutoProvider falls back to local when cloud key is missing
    client = OllamaClient(mock_mode=True)
    local = OllamaProvider(client=client, model_name="llama3.2:1b")
    auto = AutoProvider(local_provider=local, cloud_provider=cloud)

    assert auto.is_available() is True
    assert auto.get_model_name() == "llama3.2:1b"
