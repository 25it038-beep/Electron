"""Unit tests for PluginManager (manifests, permissions, dynamic execution)."""

import tempfile
from pathlib import Path
import pytest

from electorn.plugins.plugin_manager import (
    PluginManager,
    PluginManifest,
    PluginPermission,
    PluginToolDescriptor,
)


def test_builtin_plugins_registration():
    with tempfile.TemporaryDirectory() as tmp_dir:
        config_path = Path(tmp_dir) / "plugins.json"
        mgr = PluginManager(config_file=config_path)

        plugins = mgr.list_plugins()
        plugin_ids = [p["id"] for p in plugins]
        assert "windows_os" in plugin_ids
        assert "web_browser" in plugin_ids
        assert "boredom_engine" in plugin_ids
        assert "research_monitor" in plugin_ids


def test_plugin_enable_disable_persistence():
    with tempfile.TemporaryDirectory() as tmp_dir:
        config_path = Path(tmp_dir) / "plugins.json"
        mgr = PluginManager(config_file=config_path)

        # Disable boredom_engine
        assert mgr.disable_plugin("boredom_engine") is True
        boredom = next(p for p in mgr.list_plugins() if p["id"] == "boredom_engine")
        assert boredom["enabled"] is False

        # Reload new manager from same config file
        mgr2 = PluginManager(config_file=config_path)
        boredom2 = next(p for p in mgr2.list_plugins() if p["id"] == "boredom_engine")
        assert boredom2["enabled"] is False

        # Re-enable
        assert mgr2.enable_plugin("boredom_engine") is True
        boredom3 = next(p for p in mgr2.list_plugins() if p["id"] == "boredom_engine")
        assert boredom3["enabled"] is True


def test_tool_execution_permission_enforcement():
    with tempfile.TemporaryDirectory() as tmp_dir:
        config_path = Path(tmp_dir) / "plugins.json"
        mgr = PluginManager(config_file=config_path)

        # Register handler for a tool
        mgr.register_tool_handler("get_trivia", lambda: "mock_trivia")

        # Enabled execution
        res1 = mgr.execute_tool("get_trivia")
        assert res1["success"] is True
        assert res1["result"] == "mock_trivia"

        # Disable plugin and attempt execution
        mgr.disable_plugin("boredom_engine")
        res2 = mgr.execute_tool("get_trivia")
        assert res2["success"] is False
        assert "currently disabled" in res2["error"]
