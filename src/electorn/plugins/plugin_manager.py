"""Modular Plugin Architecture & Permission Enforcement Engine for Electorn AI.

Enables extensible tool manifests, permission boundaries, lifecycle management,
and dynamic plugin enable/disable controls.
"""

from __future__ import annotations

from enum import Enum
import json
import logging
from pathlib import Path
import time
from typing import Any, Callable, Dict, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class PluginPermission(str, Enum):
    """Fine-grained permission scopes for autonomous plugins."""
    READ_FILESYSTEM = "read_filesystem"
    WRITE_FILESYSTEM = "write_filesystem"
    EXECUTE_COMMANDS = "execute_commands"
    BROWSER_CONTROL = "browser_control"
    SYSTEM_METRICS = "system_metrics"
    NETWORK_REQUESTS = "network_requests"
    AUDIO_INPUT = "audio_input"
    CAMERA_INPUT = "camera_input"


class PluginToolDescriptor(BaseModel):
    """Specification of an actionable tool exposed by a plugin."""
    name: str
    description: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    required_permissions: List[PluginPermission] = Field(default_factory=list)


class PluginManifest(BaseModel):
    """Formal descriptor declaring plugin identity, permissions, and tool contracts."""
    plugin_id: str
    name: str
    version: str = "1.0.0"
    description: str
    author: str = "Harshan Seliyan"
    permissions: List[PluginPermission] = Field(default_factory=list)
    enabled: bool = True
    tools: List[PluginToolDescriptor] = Field(default_factory=list)


class PluginManager:
    """Discovers, initializes, validates, and routes execution through registered plugins."""

    def __init__(
        self,
        storage_dir: Optional[Path] = None,
        config_file: Optional[Path] = None,
    ) -> None:
        if config_file:
            self.config_file = config_file
            self.storage_dir = storage_dir or config_file.parent
        else:
            self.storage_dir = storage_dir or (Path.home() / ".electorn" / "plugins")
            self.config_file = self.storage_dir / "plugin_config.json"

        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.plugins: Dict[str, PluginManifest] = {}
        self.tool_handlers: Dict[str, Callable[..., Any]] = {}

        self._register_builtin_plugins()
        self._load_plugin_states()

    def _register_builtin_plugins(self) -> None:
        """Register primary built-in system plugins."""
        # 1. Windows OS Plugin
        self.register_plugin(
            PluginManifest(
                plugin_id="windows_os",
                name="Windows OS Automation",
                description="Desktop application launching, window focus, file organization, and system diagnostic inspection.",
                permissions=[PluginPermission.READ_FILESYSTEM, PluginPermission.WRITE_FILESYSTEM, PluginPermission.SYSTEM_METRICS],
                tools=[
                    PluginToolDescriptor(
                        name="launch_app",
                        description="Launch a desktop application by executable name or alias.",
                        parameters={"app_name": "string"},
                        required_permissions=[PluginPermission.SYSTEM_METRICS],
                    ),
                    PluginToolDescriptor(
                        name="organize_directory",
                        description="Sort files in a directory into category folders.",
                        parameters={"target_dir": "string"},
                        required_permissions=[PluginPermission.READ_FILESYSTEM, PluginPermission.WRITE_FILESYSTEM],
                    ),
                    PluginToolDescriptor(
                        name="get_diagnostics",
                        description="Inspect storage space, memory usage, and CPU load.",
                        parameters={},
                        required_permissions=[PluginPermission.SYSTEM_METRICS],
                    ),
                ],
            )
        )

        # 2. Web Browser & Research Plugin
        self.register_plugin(
            PluginManifest(
                plugin_id="web_browser",
                name="Web Browser & Autonomous Research",
                description="Playwright browser navigation, content extraction, and multi-source research report generation.",
                permissions=[PluginPermission.BROWSER_CONTROL, PluginPermission.NETWORK_REQUESTS, PluginPermission.WRITE_FILESYSTEM],
                tools=[
                    PluginToolDescriptor(
                        name="research_topic",
                        description="Conduct multi-source web research and generate a Markdown citation report.",
                        parameters={"objective": "string"},
                        required_permissions=[PluginPermission.NETWORK_REQUESTS, PluginPermission.WRITE_FILESYSTEM],
                    ),
                    PluginToolDescriptor(
                        name="search_web",
                        description="Search online web indexes for real-time snippets and URLs.",
                        parameters={"query": "string"},
                        required_permissions=[PluginPermission.NETWORK_REQUESTS],
                    ),
                ],
            )
        )

        # 3. Entertainment & Boredom Plugin
        self.register_plugin(
            PluginManifest(
                plugin_id="boredom_engine",
                name="Entertainment & Boredom Engine",
                description="Interactive text adventure games, tech trivia quizzes, coding puzzles, and startup brainstorming.",
                permissions=[],
                tools=[
                    PluginToolDescriptor(
                        name="get_trivia",
                        description="Generate an interactive multiple choice trivia challenge.",
                        parameters={},
                    ),
                    PluginToolDescriptor(
                        name="get_coding_challenge",
                        description="Generate a hands-on programming exercise with solution.",
                        parameters={},
                    ),
                ],
            )
        )

        # 4. Proactive Monitor Plugin
        self.register_plugin(
            PluginManifest(
                plugin_id="research_monitor",
                name="Proactive Information Monitor",
                description="Scheduled interest tracker discovering new AI models, developer tools, and hackathons.",
                permissions=[PluginPermission.NETWORK_REQUESTS, PluginPermission.WRITE_FILESYSTEM],
                tools=[
                    PluginToolDescriptor(
                        name="check_updates",
                        description="Run monitoring cycle to find fresh real-world updates.",
                        parameters={},
                        required_permissions=[PluginPermission.NETWORK_REQUESTS],
                    ),
                ],
            )
        )

    def register_plugin(self, manifest: PluginManifest) -> None:
        """Register a new plugin manifest in the registry."""
        self.plugins[manifest.plugin_id] = manifest

    def register_tool_handler(self, tool_name: str, handler: Callable[..., Any]) -> None:
        """Bind an executable callback handler to a tool name."""
        self.tool_handlers[tool_name] = handler

    # =========================================================================
    # 1. STATE & PERMISSION CONTROLS
    # =========================================================================

    def _load_plugin_states(self) -> None:
        """Load enabled/disabled states from persistent storage."""
        if not self.config_file.exists():
            return

        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                states = json.load(f)
                for pid, enabled in states.items():
                    if pid in self.plugins:
                        self.plugins[pid].enabled = bool(enabled)
        except Exception as e:
            logger.debug("Failed loading plugin states: %s", e)

    def _save_plugin_states(self) -> None:
        """Persist plugin states."""
        try:
            states = {pid: p.enabled for pid, p in self.plugins.items()}
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(states, f, indent=2)
        except Exception as e:
            logger.debug("Failed saving plugin states: %s", e)

    def enable_plugin(self, plugin_id: str) -> bool:
        """Enable a registered plugin."""
        if plugin_id in self.plugins:
            self.plugins[plugin_id].enabled = True
            self._save_plugin_states()
            return True
        return False

    def disable_plugin(self, plugin_id: str) -> bool:
        """Disable a registered plugin."""
        if plugin_id in self.plugins:
            self.plugins[plugin_id].enabled = False
            self._save_plugin_states()
            return True
        return False

    def list_plugins(self) -> List[Dict[str, Any]]:
        """Return list of all registered plugins with statuses."""
        return [
            {
                "id": p.plugin_id,
                "name": p.name,
                "version": p.version,
                "description": p.description,
                "enabled": p.enabled,
                "tools_count": len(p.tools),
                "permissions": [perm.value for perm in p.permissions],
            }
            for p in self.plugins.values()
        ]

    # =========================================================================
    # 2. EXECUTION DISPATCH & PERMISSION ENFORCEMENT
    # =========================================================================

    def execute_tool(self, tool_name: str, **kwargs: Any) -> Dict[str, Any]:
        """Execute a tool while enforcing plugin enablement and permission rules."""
        # Find owning plugin
        owning_plugin: Optional[PluginManifest] = None
        target_tool: Optional[PluginToolDescriptor] = None

        for p in self.plugins.values():
            for t in p.tools:
                if t.name == tool_name:
                    owning_plugin = p
                    target_tool = t
                    break
            if owning_plugin:
                break

        if not owning_plugin or not target_tool:
            return {"success": False, "error": f"Tool '{tool_name}' is not registered in any plugin."}

        if not owning_plugin.enabled:
            return {
                "success": False,
                "error": f"Tool '{tool_name}' cannot be executed because plugin '{owning_plugin.name}' is currently disabled.",
            }

        handler = self.tool_handlers.get(tool_name)
        if not handler:
            return {"success": False, "error": f"No execution handler registered for tool '{tool_name}'."}

        try:
            result = handler(**kwargs)
            return {"success": True, "tool": tool_name, "plugin": owning_plugin.plugin_id, "result": result}
        except Exception as e:
            return {"success": False, "tool": tool_name, "error": str(e)}
