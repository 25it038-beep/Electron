"""Natural language element descriptor resolution into exact screen coordinates."""

from __future__ import annotations

from typing import List, Optional, Tuple

from ..types import ComputerState, UIElement


class VisualGrounding:
    """Translates 'the Run button' or 'the search bar' into screen coordinates."""

    def resolve_target(self, description: str, state: ComputerState) -> Optional[Tuple[int, int]]:
        clean = description.strip().lower()

        # 1. Match detected UI elements
        for elem in state.visible_elements:
            if elem.label.lower() in clean or clean in elem.label.lower():
                return elem.location

        # 2. Match OCR tokens
        for tok in state.ocr_tokens:
            if clean in tok.text.lower():
                return tok.location

        # 3. Geometric landmarks
        w = state.screen_resolution.get("width", 1920)
        h = state.screen_resolution.get("height", 1080)

        if "search" in clean or "address" in clean or "url" in clean:
            return (int(w * 0.45), 82)
        if "run" in clean or "play" in clean:
            return (int(w * 0.92), 48)
        if "center" in clean or "middle" in clean or "editor" in clean:
            return (int(w * 0.5), int(h * 0.5))

        return None

    def find_target(
        self,
        description: str,
        candidate_elements: Optional[List[UIElement]] = None,
    ) -> Optional[UIElement]:
        clean = description.strip().lower()
        if candidate_elements:
            for elem in candidate_elements:
                if elem.label.lower() in clean or clean in elem.label.lower():
                    return elem
        return None
