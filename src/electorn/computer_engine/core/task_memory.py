"""
Task Memory: Records past autonomous computer operations, outcomes, and learned procedures.
"""

from typing import List, Optional, Dict, Any
from electorn.computer_engine.types import TaskPlan


class TaskMemory:
    def __init__(self) -> None:
        self._history: List[TaskPlan] = []
        self._strategies: Dict[str, Any] = {}

    def record_completed_task(self, plan: TaskPlan) -> None:
        self._history.append(plan)
        # Learn procedure mapping
        if plan.status == "completed":
            self._strategies[plan.original_instruction.lower()] = {
                "target_app": plan.target_application,
                "step_count": len(plan.steps),
                "steps": [s.description for s in plan.steps],
            }

    def get_recent_tasks(self, limit: int = 10) -> List[TaskPlan]:
        return self._history[-limit:]

    def get_last_task(self) -> Optional[TaskPlan]:
        return self._history[-1] if self._history else None

    def find_strategy(self, query: str) -> Optional[Dict[str, Any]]:
        clean = query.lower()
        return self._strategies.get(clean)

    def clear(self) -> None:
        self._history.clear()
        self._strategies.clear()
