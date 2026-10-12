"""Task history management and sanitized export for Electorn AI."""

from __future__ import annotations

import json
import re
from typing import Any, Optional

from storage.database import TaskDatabase, TaskRecord


class HistoryManager:
    """Manages historical task logs with privacy and credential redaction."""

    SENSITIVE_PATTERNS = [
        (r"(?i)(api[_-]?key\s*[:=]\s*['\"]?)([\w\-]{8,})(['\"]?)", r"\1[REDACTED]\3"),
        (r"(?i)(password\s*[:=]\s*['\"]?)([^'\"\s]+)(['\"]?)", r"\1[REDACTED]\3"),
        (r"(?i)(bearer\s+)([a-zA-Z0-9_\-\.]{15,})", r"\1[REDACTED]"),
        (r"(?i)(token\s*[:=]\s*['\"]?)([\w\-]{8,})(['\"]?)", r"\1[REDACTED]\3"),
    ]

    def __init__(self, db: TaskDatabase) -> None:
        self.db = db

    def redact(self, text: str) -> str:
        """Strip sensitive credentials and tokens from text."""
        sanitized = text
        for pattern, replacement in self.SENSITIVE_PATTERNS:
            sanitized = re.sub(pattern, replacement, sanitized)
        return sanitized

    def get_recent_tasks(self, limit: int = 50) -> list[dict[str, Any]]:
        """Return list of recent tasks with parsed plan and sanitized strings."""
        records = self.db.list_tasks(limit=limit)
        results = []
        for r in records:
            plan = []
            try:
                plan = json.loads(r.plan_json)
            except Exception:
                pass
            results.append({
                "task_id": r.task_id,
                "transcript": self.redact(r.transcript),
                "objective": self.redact(r.objective),
                "status": r.status,
                "start_time": r.start_time,
                "end_time": r.end_time,
                "duration_sec": round(r.end_time - r.start_time, 2) if r.end_time else None,
                "steps_count": len(plan),
                "error": self.redact(r.error_message) if r.error_message else None,
            })
        return results

    def export_history_json(self, limit: int = 100) -> str:
        """Export sanitized JSON task history."""
        tasks = self.get_recent_tasks(limit=limit)
        return json.dumps(tasks, indent=2)

    def delete_task(self, task_id: str) -> bool:
        """Delete specific task from history."""
        return self.db.delete_task(task_id)
