"""Screen perception analyzer constructing structured ComputerState."""

from __future__ import annotations

import time
from typing import Optional

from ..controllers.mouse_controller import MouseController
from ..controllers.screen_controller import ScreenController
from ..controllers.window_controller import WindowController
from ..types import ComputerState
from .element_detector import UIElementDetector
from .ocr_processor import OCRProcessor


class ScreenAnalyzer:
    """Captures and synthesizes full computer perception context."""

    def __init__(
        self,
        screen_ctrl: Optional[ScreenController] = None,
        window_ctrl: Optional[WindowController] = None,
        mouse_ctrl: Optional[MouseController] = None,
        detector: Optional[UIElementDetector] = None,
        ocr: Optional[OCRProcessor] = None,
    ) -> None:
        self.screen_ctrl = screen_ctrl or ScreenController()
        self.window_ctrl = window_ctrl or WindowController()
        self.mouse_ctrl = mouse_ctrl or MouseController()
        self.detector = detector or UIElementDetector()
        self.ocr = ocr or OCRProcessor()

    def analyze_state(self, include_ocr: bool = True) -> ComputerState:
        """Capture active window, cursor, resolution, and UI elements into ComputerState."""
        win = self.window_ctrl.get_active_window()
        res = self.screen_ctrl.get_resolution()
        cursor = self.mouse_ctrl.get_position()

        elements = self.detector.detect_elements(win["title"], res)
        ocr_tokens = self.ocr.extract_tokens(win["title"], res) if include_ocr else []

        return ComputerState(
            active_application=win["process_name"],
            active_window=win["title"],
            cursor_location=cursor,
            screen_resolution={"width": res[0], "height": res[1]},
            visible_elements=elements,
            ocr_tokens=ocr_tokens,
            task_status="ready",
            automation_enabled=True,
            is_paused=False,
            emergency_stopped=False,
            timestamp=time.time(),
        )

    def get_current_state(self) -> ComputerState:
        """Alias for analyze_state."""
        return self.analyze_state()
