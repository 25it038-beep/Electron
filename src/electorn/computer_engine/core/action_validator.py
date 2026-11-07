"""
Core Action Validator: Verifies action preconditions and postconditions.
"""

from typing import Optional, Dict, Any
from electorn.computer_engine.types import (
    ActionPayload,
    ActionResult,
    TaskStep,
    ComputerState,
)


class CoreActionValidator:
    def validate_preconditions(
        self,
        action: ActionPayload,
        state: Optional[ComputerState] = None,
    ) -> Dict[str, Any]:
        """Verify preconditions before dispatching to physical hardware."""
        if action.category == "mouse" and action.action_type in ("click", "double_click", "right_click"):
            if action.coordinates is not None:
                x, y = action.coordinates
                if x < 0 or y < 0:
                    return {"valid": False, "reason": f"Invalid screen coordinates: ({x}, {y})"}

        if action.category == "keyboard" and action.action_type == "type_text":
            if action.text is None:
                return {"valid": False, "reason": "No text supplied for type_text action."}

        return {"valid": True}

    def validate_postconditions(
        self,
        step: TaskStep,
        result: ActionResult,
        after_state: Optional[ComputerState] = None,
    ) -> Dict[str, Any]:
        """Verify postconditions after execution."""
        if not result.success:
            return {
                "valid": False,
                "reason": result.error or "Action failed execution.",
            }
        return {"valid": True}
