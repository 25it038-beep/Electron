"""
HS Autonomous Computer Engine (HACE)
Full-featured desktop automation, visual grounding, mouse/keyboard control, and safety gates.
"""

from electorn.computer_engine.core.computer_engine import ComputerEngine
from electorn.computer_engine.safety.emergency_stop import EmergencyStop
from electorn.computer_engine.safety.permission_manager import PermissionManager
from electorn.computer_engine.safety.action_approval import ActionApproval

__all__ = [
    "ComputerEngine",
    "EmergencyStop",
    "PermissionManager",
    "ActionApproval",
]
