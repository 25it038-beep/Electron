"""Integration tests for OllamaManager and auto-start lifecycle."""

import pytest
try:
    from electorn.providers.ollama_manager import OllamaManager
    from electorn.providers.local_llm import OllamaLocalProvider
except ImportError:
    from providers.ollama_manager import OllamaManager
    from providers.local_llm import OllamaLocalProvider


def test_ollama_manager_discovery():
    mgr = OllamaManager()
    exe = mgr.find_executable()
    assert exe is not None, "Ollama executable should be discovered"
    assert mgr.is_installed() is True


def test_ollama_manager_ready_and_models():
    mgr = OllamaManager()
    res = mgr.ensure_ready()
    assert res["installed"] is True
    assert res["running"] is True
    assert res["model_ready"] is True
    assert len(mgr.list_models()) > 0


def test_ollama_local_provider_auto_start():
    provider = OllamaLocalProvider(auto_start=True)
    assert provider.is_available() is True
    assert provider.model_name in ("llama3.2:1b", "llama3.2:latest", "llama3.2")
