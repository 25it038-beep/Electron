"""Pre-execution coordinate and boundary validation."""

from __future__ import annotations

from typing import List, Optional, Tuple

from ..types import ActionPayload, ComputerState


class ActionValidator:
    """Validates and sanitizes coordinates and payloads before physical dispatch."""

    def validate_action(self, action: ActionPayload, state: Optional[ComputerState] = None) -> Tuple[bool, List[str]]:
        errors: List[str] = []

        if action.category == "mouse" and action.coordinates is not None:
            x, y = action.coordinates
            max_w = state.screen_resolution.get("width", 3840) if state else 3840
            max_h = state.screen_resolution.get("height", 2160) if state else 2160

            if x < 0 or x > max_w or y < 0 or y > max_h:
                errors.append(f"Coordinates ({x}, {y}) exceed screen resolution [0..{max_w}, 0..{max_h}].")

        if action.category == "keyboard":
            if action.type == "type_text" and action.text is None:
                errors.append("Keyboard typing action requires 'text' parameter.")

        if action.category == "browser" and action.type == "open_url":
            if not action.url or not (action.url.startswith("http://") or action.url.startswith("https://")):
                errors.append(f"Invalid URL: {action.url}")

        return (len(errors) == 0, errors)
