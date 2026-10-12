"""Tool Registry mapping action names to validated automation implementations."""

from __future__ import annotations

from typing import Any, Callable, Optional

from automation.browser_automation import SeleniumBrowserAutomation
from automation.file_automation import FileAutomation
from automation.os_automation import WindowsOSAutomation
from automation.process_runner import ControlledProcessRunner


class ToolRegistry:
    """Central directory of executable tools with input parameter validation."""

    def __init__(
        self,
        os_engine: Optional[WindowsOSAutomation] = None,
        browser_engine: Optional[SeleniumBrowserAutomation] = None,
        file_engine: Optional[FileAutomation] = None,
        process_runner: Optional[ControlledProcessRunner] = None,
    ) -> None:
        self.os_engine = os_engine or WindowsOSAutomation()
        self.browser_engine = browser_engine or SeleniumBrowserAutomation()
        self.file_engine = file_engine or FileAutomation()
        self.process_runner = process_runner or ControlledProcessRunner()

        self._tools: dict[str, dict[str, Any]] = {}
        self._register_all_tools()

    def _register_all_tools(self) -> None:
        # Browser tools
        self._register("browser.open_url", self._wrap_browser_open, "Open a website URL in browser", ["url"])
        self._register("browser.search", self._wrap_browser_search, "Search Google via browser", ["query"])
        self._register("browser.click", self._wrap_browser_click, "Click a webpage element by CSS selector", ["selector"])
        self._register("browser.type", self._wrap_browser_type, "Type text into a webpage input field", ["selector", "text"])
        self._register("browser.scroll", self._wrap_browser_scroll, "Scroll browser page (up/down/top/bottom)", ["direction"])
        self._register("browser.navigate", self._wrap_browser_navigate, "Navigate browser (back/forward/refresh)", ["action"])
        self._register("browser.extract_table", self._wrap_browser_extract_table, "Extract HTML table from webpage", [])
        self._register("browser.export_csv", self._wrap_browser_export_csv, "Extract webpage table and save as CSV", ["file_path"])
        self._register("browser.screenshot", self._wrap_browser_screenshot, "Capture screenshot of browser", ["filename"])
        self._register("browser.close", self._wrap_browser_close, "Close browser session", [])

        # OS tools
        self._register("os.launch_app", self._wrap_os_launch, "Launch desktop application", ["app"])
        self._register("os.close_app", self._wrap_os_close, "Close desktop application", ["app"])
        self._register("os.minimize_windows", self._wrap_os_minimize, "Minimize all windows to desktop", [])
        self._register("os.maximize_window", self._wrap_os_maximize, "Maximize active window", [])
        self._register("os.switch_window", self._wrap_os_switch, "Switch active window (Alt+Tab)", [])
        self._register("os.close_window", self._wrap_os_close_window, "Close active window (Alt+F4)", [])
        self._register("os.lock", self._wrap_os_lock, "Lock computer workstation", [])
        self._register("os.type_text", self._wrap_os_type, "Type text into focused application", ["text"])
        self._register("os.press_key", self._wrap_os_press, "Press specific keyboard key", ["key"])
        self._register("os.volume", self._wrap_os_volume, "Adjust volume (up/down/mute)", ["action"])
        self._register("os.media", self._wrap_os_media, "Media control (play/pause/next/prev)", ["action"])
        self._register("os.system_specs", self._wrap_os_specs, "Inspect system CPU, RAM, Disk, Battery", [])

        # File tools
        self._register("file.create_folder", self._wrap_file_create_folder, "Create folder directory", ["path"])
        self._register("file.create_file", self._wrap_file_create_file, "Create or overwrite text file", ["path", "content"])
        self._register("file.read_file", self._wrap_file_read_file, "Read text file contents", ["path"])
        self._register("file.move_file", self._wrap_file_move, "Move or rename file", ["src", "dst"])
        self._register("file.copy_file", self._wrap_file_copy, "Copy file to destination", ["src", "dst"])
        self._register("file.organize_files", self._wrap_file_organize, "Organize files by extension into folder", ["source_dir", "target_dir", "ext"])
        self._register("file.open_path", self._wrap_file_open, "Open file or folder in File Explorer", ["path"])

        # Process tools
        self._register("process.run_command", self._wrap_process_run, "Execute shell command in controlled subprocess", ["command"])

    def _register(self, name: str, handler: Callable[..., Any], description: str, required_params: list[str]) -> None:
        self._tools[name] = {
            "name": name,
            "handler": handler,
            "description": description,
            "required_params": required_params,
        }

    def has_tool(self, name: str) -> bool:
        return name in self._tools

    def get_tool_metadata(self) -> list[dict[str, Any]]:
        return [
            {"name": k, "description": v["description"], "required_params": v["required_params"]}
            for k, v in self._tools.items()
        ]

    def execute_tool(self, name: str, params: dict[str, Any]) -> dict[str, Any]:
        """Validate parameters and invoke tool handler."""
        if name not in self._tools:
            return {"success": False, "message": f"Tool '{name}' is not registered."}

        tool = self._tools[name]
        for req in tool["required_params"]:
            if req not in params:
                return {"success": False, "message": f"Missing required parameter '{req}' for tool '{name}'."}

        try:
            return tool["handler"](params)
        except Exception as err:
            return {"success": False, "message": f"Execution error in '{name}': {err}"}

    # Browser Wrappers
    def _wrap_browser_open(self, p: dict[str, Any]) -> dict[str, Any]:
        return self.browser_engine.open_url(p["url"], headless=p.get("headless", False))

    def _wrap_browser_search(self, p: dict[str, Any]) -> dict[str, Any]:
        return self.browser_engine.search(p["query"], headless=p.get("headless", False))

    def _wrap_browser_click(self, p: dict[str, Any]) -> dict[str, Any]:
        return self.browser_engine.click_element(p["selector"], by=p.get("by", "css"))

    def _wrap_browser_type(self, p: dict[str, Any]) -> dict[str, Any]:
        return self.browser_engine.type_into_field(p["selector"], p["text"], by=p.get("by", "css"), press_enter=p.get("press_enter", False))

    def _wrap_browser_scroll(self, p: dict[str, Any]) -> dict[str, Any]:
        return self.browser_engine.scroll(p["direction"], amount=p.get("amount", 600))

    def _wrap_browser_navigate(self, p: dict[str, Any]) -> dict[str, Any]:
        return self.browser_engine.navigate(p["action"])

    def _wrap_browser_extract_table(self, p: dict[str, Any]) -> dict[str, Any]:
        return self.browser_engine.extract_table(p.get("selector", "table"))

    def _wrap_browser_export_csv(self, p: dict[str, Any]) -> dict[str, Any]:
        return self.browser_engine.export_table_to_csv(p["file_path"], table_selector=p.get("selector", "table"))

    def _wrap_browser_screenshot(self, p: dict[str, Any]) -> dict[str, Any]:
        return self.browser_engine.capture_screenshot(p["filename"])

    def _wrap_browser_close(self, p: dict[str, Any]) -> dict[str, Any]:
        return self.browser_engine.close()

    # OS Wrappers
    def _wrap_os_launch(self, p: dict[str, Any]) -> dict[str, Any]:
        return self.os_engine.launch_app(p["app"])

    def _wrap_os_close(self, p: dict[str, Any]) -> dict[str, Any]:
        return self.os_engine.close_app(p["app"], force=p.get("force", False))

    def _wrap_os_minimize(self, p: dict[str, Any]) -> dict[str, Any]:
        msg = self.os_engine.minimize_all_windows()
        return {"success": True, "message": msg}

    def _wrap_os_maximize(self, p: dict[str, Any]) -> dict[str, Any]:
        msg = self.os_engine.maximize_window()
        return {"success": True, "message": msg}

    def _wrap_os_switch(self, p: dict[str, Any]) -> dict[str, Any]:
        msg = self.os_engine.switch_window()
        return {"success": True, "message": msg}

    def _wrap_os_close_window(self, p: dict[str, Any]) -> dict[str, Any]:
        msg = self.os_engine.close_active_window()
        return {"success": True, "message": msg}

    def _wrap_os_lock(self, p: dict[str, Any]) -> dict[str, Any]:
        msg = self.os_engine.lock_workstation()
        return {"success": True, "message": msg}

    def _wrap_os_type(self, p: dict[str, Any]) -> dict[str, Any]:
        msg = self.os_engine.type_text(p["text"])
        return {"success": True, "message": msg}

    def _wrap_os_press(self, p: dict[str, Any]) -> dict[str, Any]:
        msg = self.os_engine.press_key(p["key"])
        return {"success": True, "message": msg}

    def _wrap_os_volume(self, p: dict[str, Any]) -> dict[str, Any]:
        msg = self.os_engine.control_volume(p["action"])
        return {"success": True, "message": msg}

    def _wrap_os_media(self, p: dict[str, Any]) -> dict[str, Any]:
        msg = self.os_engine.control_media(p["action"])
        return {"success": True, "message": msg}

    def _wrap_os_specs(self, p: dict[str, Any]) -> dict[str, Any]:
        specs = self.os_engine.get_system_specs_text()
        return {"success": True, "message": specs}

    # File Wrappers
    def _wrap_file_create_folder(self, p: dict[str, Any]) -> dict[str, Any]:
        return self.file_engine.create_folder(p["path"])

    def _wrap_file_create_file(self, p: dict[str, Any]) -> dict[str, Any]:
        return self.file_engine.create_file(p["path"], content=p.get("content", ""), allow_overwrite=p.get("allow_overwrite", True))

    def _wrap_file_read_file(self, p: dict[str, Any]) -> dict[str, Any]:
        return self.file_engine.read_file(p["path"])

    def _wrap_file_move(self, p: dict[str, Any]) -> dict[str, Any]:
        return self.file_engine.move_file(p["src"], p["dst"])

    def _wrap_file_copy(self, p: dict[str, Any]) -> dict[str, Any]:
        return self.file_engine.copy_file(p["src"], p["dst"])

    def _wrap_file_organize(self, p: dict[str, Any]) -> dict[str, Any]:
        return self.file_engine.organize_files_by_extension(p["source_dir"], p["target_dir"], p["ext"])

    def _wrap_file_open(self, p: dict[str, Any]) -> dict[str, Any]:
        return self.file_engine.open_path_in_explorer(p["path"])

    # Process Runner Wrapper
    def _wrap_process_run(self, p: dict[str, Any]) -> dict[str, Any]:
        return self.process_runner.run_command(p["command"], cwd=p.get("cwd"), timeout_sec=p.get("timeout_sec"))
