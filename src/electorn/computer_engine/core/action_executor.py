"""
Action Executor: Dispatches validated actions to physical controllers with safety gates.
"""

import time
import subprocess
from typing import Optional, Dict, Any

from electorn.computer_engine.types import ActionPayload, ActionResult
from electorn.computer_engine.controllers.mouse_controller import MouseController
from electorn.computer_engine.controllers.keyboard_controller import KeyboardController
from electorn.computer_engine.controllers.window_controller import WindowController
from electorn.computer_engine.browser.browser_controller import BrowserController
from electorn.computer_engine.safety.permission_manager import PermissionManager
from electorn.computer_engine.safety.action_approval import ActionApproval
from electorn.computer_engine.safety.emergency_stop import EmergencyStop
from electorn.computer_engine.perception.visual_grounding import VisualGrounding
from electorn.computer_engine.perception.screen_analyzer import ScreenAnalyzer


class ActionExecutor:
    def __init__(
        self,
        mouse: Optional[MouseController] = None,
        keyboard: Optional[KeyboardController] = None,
        window: Optional[WindowController] = None,
        browser: Optional[BrowserController] = None,
        permission: Optional[PermissionManager] = None,
        approval: Optional[ActionApproval] = None,
        grounding: Optional[VisualGrounding] = None,
        analyzer: Optional[ScreenAnalyzer] = None,
    ) -> None:
        self.mouse = mouse or MouseController()
        self.keyboard = keyboard or KeyboardController()
        self.window = window or WindowController()
        self.browser = browser or BrowserController()
        self.permission = permission or PermissionManager()
        self.approval = approval or ActionApproval()
        self.emergency_stop = EmergencyStop.get_instance()
        self.grounding = grounding or VisualGrounding()
        self.analyzer = analyzer or ScreenAnalyzer()

    def execute(self, action: ActionPayload) -> ActionResult:
        start_time = time.time()

        # 1. Emergency Stop Check
        if self.emergency_stop.check():
            return ActionResult(
                action_id=action.action_id,
                success=False,
                message="Action aborted by Emergency Stop.",
                error=self.emergency_stop.get_reason(),
                duration_ms=0.0,
            )

        # 2. Safety Risk Gate
        risk = self.permission.evaluate_risk(action)
        if risk == "blocked":
            return ActionResult(
                action_id=action.action_id,
                success=False,
                message=f"Action '{action.description}' is blocked for safety.",
                error="ActionBlockedByPolicy",
                duration_ms=0.0,
            )

        if self.permission.requires_confirmation(action):
            status = self.approval.get_status(action.action_id)
            if status != "approved":
                return ActionResult(
                    action_id=action.action_id,
                    success=False,
                    message=f"Action requires explicit approval: '{action.description}'",
                    error="ApprovalRequired",
                    duration_ms=0.0,
                )

        # 3. Dispatch to Subsystem
        try:
            if action.category == "mouse":
                return self._execute_mouse(action, start_time)
            elif action.category == "keyboard":
                return self._execute_keyboard(action, start_time)
            elif action.category == "window":
                return self._execute_window(action, start_time)
            elif action.category == "browser":
                return self._execute_browser(action, start_time)
            elif action.category == "system":
                return self._execute_system(action, start_time)
            else:
                return ActionResult(
                    action_id=action.action_id,
                    success=False,
                    message=f"Unknown action category '{action.category}'",
                    error="UnknownCategory",
                    duration_ms=(time.time() - start_time) * 1000,
                )
        except Exception as e:
            return ActionResult(
                action_id=action.action_id,
                success=False,
                message=f"Execution error: {str(e)}",
                error=str(e),
                duration_ms=(time.time() - start_time) * 1000,
            )

    def _execute_mouse(self, action: ActionPayload, start_time: float) -> ActionResult:
        coords = action.coordinates

        # Visual grounding lookup if no coordinates provided
        if coords is None and action.target:
            grounded = self.grounding.find_target(action.target)
            if grounded:
                coords = (grounded.center_x, grounded.center_y)

        if action.action_type in ("click", "left_click"):
            if coords:
                ok = self.mouse.click(coords[0], coords[1])
            else:
                ok = self.mouse.click()
            return ActionResult(
                action_id=action.action_id,
                success=ok,
                message="Clicked successfully" if ok else "Click failed or aborted by safety.",
                duration_ms=(time.time() - start_time) * 1000,
            )
        elif action.action_type == "double_click":
            if coords:
                ok = self.mouse.double_click(coords[0], coords[1])
            else:
                ok = self.mouse.double_click()
            return ActionResult(
                action_id=action.action_id,
                success=ok,
                message="Double clicked",
                duration_ms=(time.time() - start_time) * 1000,
            )
        elif action.action_type == "right_click":
            if coords:
                ok = self.mouse.right_click(coords[0], coords[1])
            else:
                ok = self.mouse.right_click()
            return ActionResult(
                action_id=action.action_id,
                success=ok,
                message="Right clicked",
                duration_ms=(time.time() - start_time) * 1000,
            )
        elif action.action_type == "move":
            if coords:
                ok = self.mouse.move_to(coords[0], coords[1])
                return ActionResult(
                    action_id=action.action_id,
                    success=ok,
                    message=f"Moved to ({coords[0]}, {coords[1]})",
                    duration_ms=(time.time() - start_time) * 1000,
                )
        elif action.action_type == "scroll":
            delta = int(action.parameters.get("delta", 3)) if action.parameters else 3
            ok = self.mouse.scroll(delta)
            return ActionResult(
                action_id=action.action_id,
                success=ok,
                message=f"Scrolled {delta} clicks",
                duration_ms=(time.time() - start_time) * 1000,
            )

        return ActionResult(
            action_id=action.action_id,
            success=False,
            message=f"Unsupported mouse action type: {action.action_type}",
            duration_ms=(time.time() - start_time) * 1000,
        )

    def _execute_keyboard(self, action: ActionPayload, start_time: float) -> ActionResult:
        if action.action_type == "type_text":
            ok = self.keyboard.type_text(action.text or "")
            return ActionResult(
                action_id=action.action_id,
                success=ok,
                message=f"Typed text: '{action.text}'",
                duration_ms=(time.time() - start_time) * 1000,
            )
        elif action.action_type == "shortcut":
            keys = action.keys or []
            ok = self.keyboard.hotkey(*keys)
            return ActionResult(
                action_id=action.action_id,
                success=ok,
                message=f"Pressed shortcut: {'+'.join(keys)}",
                duration_ms=(time.time() - start_time) * 1000,
            )
        elif action.action_type == "press_key":
            key = action.parameters.get("key", "enter") if action.parameters else "enter"
            ok = self.keyboard.press_key(key)
            return ActionResult(
                action_id=action.action_id,
                success=ok,
                message=f"Pressed key: {key}",
                duration_ms=(time.time() - start_time) * 1000,
            )

        return ActionResult(
            action_id=action.action_id,
            success=False,
            message=f"Unsupported keyboard action type: {action.action_type}",
            duration_ms=(time.time() - start_time) * 1000,
        )

    def _execute_window(self, action: ActionPayload, start_time: float) -> ActionResult:
        if action.action_type == "launch_app":
            target = action.target or "cmd"
            ok = self.window.launch_application(target)
            return ActionResult(
                action_id=action.action_id,
                success=ok,
                message=f"Launched application '{target}'",
                duration_ms=(time.time() - start_time) * 1000,
            )
        elif action.action_type == "focus_window":
            ok = self.window.focus_window(action.target or "")
            return ActionResult(
                action_id=action.action_id,
                success=ok,
                message=f"Focused window matching '{action.target}'",
                duration_ms=(time.time() - start_time) * 1000,
            )
        elif action.action_type == "close_window":
            ok = self.window.close_window(action.target or "")
            return ActionResult(
                action_id=action.action_id,
                success=ok,
                message=f"Closed window '{action.target}'",
                duration_ms=(time.time() - start_time) * 1000,
            )

        return ActionResult(
            action_id=action.action_id,
            success=False,
            message=f"Unsupported window action: {action.action_type}",
            duration_ms=(time.time() - start_time) * 1000,
        )

    def _execute_browser(self, action: ActionPayload, start_time: float) -> ActionResult:
        if action.action_type == "open_url" and action.url:
            ok = self.browser.open_url(action.url)
            return ActionResult(
                action_id=action.action_id,
                success=ok,
                message=f"Navigated to '{action.url}'",
                duration_ms=(time.time() - start_time) * 1000,
            )
        elif action.action_type == "search":
            query = action.parameters.get("query", "") if action.parameters else ""
            ok = self.browser.search(query)
            return ActionResult(
                action_id=action.action_id,
                success=ok,
                message=f"Executed browser search for '{query}'",
                duration_ms=(time.time() - start_time) * 1000,
            )

        return ActionResult(
            action_id=action.action_id,
            success=False,
            message=f"Unsupported browser action: {action.action_type}",
            duration_ms=(time.time() - start_time) * 1000,
        )

    def _execute_system(self, action: ActionPayload, start_time: float) -> ActionResult:
        cmd = action.parameters.get("command") if action.parameters else action.description
        if not cmd:
            return ActionResult(
                action_id=action.action_id,
                success=True,
                message="No-op system instruction completed.",
                duration_ms=(time.time() - start_time) * 1000,
            )

        try:
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
            return ActionResult(
                action_id=action.action_id,
                success=res.returncode == 0,
                message=f"Command output: {res.stdout.strip() or res.stderr.strip()}",
                duration_ms=(time.time() - start_time) * 1000,
            )
        except Exception as e:
            return ActionResult(
                action_id=action.action_id,
                success=False,
                message=f"Failed to execute command: {e}",
                error=str(e),
                duration_ms=(time.time() - start_time) * 1000,
            )
