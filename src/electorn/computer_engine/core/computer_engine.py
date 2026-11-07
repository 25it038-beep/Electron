"""
Master Entry Point: HS Autonomous Computer Engine (HACE) in Python.
"""

from typing import Optional, Dict, Any, List

from electorn.computer_engine.controllers.mouse_controller import MouseController
from electorn.computer_engine.controllers.keyboard_controller import KeyboardController
from electorn.computer_engine.controllers.clipboard_controller import ClipboardController
from electorn.computer_engine.controllers.screen_controller import ScreenController
from electorn.computer_engine.controllers.window_controller import WindowController

from electorn.computer_engine.perception.screen_analyzer import ScreenAnalyzer
from electorn.computer_engine.perception.element_detector import UIElementDetector
from electorn.computer_engine.perception.ocr_processor import OCRProcessor
from electorn.computer_engine.perception.visual_grounding import VisualGrounding

from electorn.computer_engine.browser.browser_controller import BrowserController
from electorn.computer_engine.browser.browser_navigator import BrowserNavigator
from electorn.computer_engine.browser.browser_agent import BrowserAgent

from electorn.computer_engine.safety.permission_manager import PermissionManager
from electorn.computer_engine.safety.action_approval import ActionApproval
from electorn.computer_engine.safety.emergency_stop import EmergencyStop
from electorn.computer_engine.safety.action_validator import ActionValidator as SafetyValidator

from electorn.computer_engine.core.action_planner import ActionPlanner
from electorn.computer_engine.core.action_executor import ActionExecutor
from electorn.computer_engine.core.action_validator import CoreActionValidator
from electorn.computer_engine.core.task_manager import TaskManager
from electorn.computer_engine.core.task_memory import TaskMemory

from electorn.computer_engine.types import (
    TaskPlan,
    ActionResult,
    ActionPayload,
    ComputerState,
)


class ComputerEngine:
    def __init__(self) -> None:
        # Controllers
        self.mouse = MouseController()
        self.keyboard = KeyboardController()
        self.clipboard = ClipboardController()
        self.screen = ScreenController()
        self.window = WindowController()

        # Perception
        self.analyzer = ScreenAnalyzer()
        self.element_detector = UIElementDetector()
        self.ocr = OCRProcessor()
        self.grounding = VisualGrounding()

        # Browser
        self.browser = BrowserController()
        self.navigator = BrowserNavigator()
        self.browser_agent = BrowserAgent(self.browser, self.navigator)

        # Safety
        self.permissions = PermissionManager()
        self.approval = ActionApproval()
        self.emergency_stop = EmergencyStop.get_instance()
        self.safety_validator = SafetyValidator()

        # Core
        self.planner = ActionPlanner()
        self.validator = CoreActionValidator()
        self.memory = TaskMemory()
        self.executor = ActionExecutor(
            mouse=self.mouse,
            keyboard=self.keyboard,
            window=self.window,
            browser=self.browser,
            permission=self.permissions,
            approval=self.approval,
            grounding=self.grounding,
            analyzer=self.analyzer,
        )
        self.task_manager = TaskManager(
            planner=self.planner,
            executor=self.executor,
            validator=self.validator,
            memory=self.memory,
            analyzer=self.analyzer,
        )

    def execute_instruction(self, instruction: str) -> TaskPlan:
        """High-level autonomous execution of natural language instructions."""
        return self.task_manager.execute_instruction(instruction)

    def execute_action(self, action: ActionPayload) -> ActionResult:
        """Execute a single atomic computer action."""
        return self.executor.execute(action)

    def get_state(self) -> ComputerState:
        """Capture current computer state."""
        return self.analyzer.get_current_state()

    def stop_all(self, reason: str = "User invoked Emergency Stop") -> None:
        """Emergency stop: halts all ongoing actions immediately."""
        self.emergency_stop.trigger(reason)

    def reset_safety(self) -> None:
        """Reset emergency stop to resume operations."""
        self.emergency_stop.reset()
