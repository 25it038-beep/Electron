"""SQLite local database for tasks, audit logs, and workflow persistence."""

from __future__ import annotations

import json
import pathlib
import sqlite3
import time
from dataclasses import asdict, dataclass
from typing import Any, Optional


@dataclass
class TaskRecord:
    """Record of a complete voice automation task."""
    task_id: str
    transcript: str
    objective: str
    status: str  # "completed", "failed", "cancelled", "running"
    start_time: float
    end_time: Optional[float] = None
    plan_json: str = "[]"
    verification_json: str = "{}"
    error_message: Optional[str] = None


@dataclass
class StepRecord:
    """Record of an individual step execution."""
    task_id: str
    step_index: int
    action: str
    parameters_json: str
    status: str
    result: str
    duration_ms: int


class TaskDatabase:
    """Thread-safe SQLite storage for Electorn AI tasks and audit events."""

    def __init__(self, db_path: Optional[str | pathlib.Path] = None) -> None:
        if db_path is None:
            db_dir = pathlib.Path.home() / ".electorn"
            db_dir.mkdir(parents=True, exist_ok=True)
            self.db_path = str(db_dir / "electorn_tasks.db")
        else:
            self.db_path = str(db_path)
            pathlib.Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Create database tables if they do not exist."""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    transcript TEXT NOT NULL,
                    objective TEXT NOT NULL,
                    status TEXT NOT NULL,
                    start_time REAL NOT NULL,
                    end_time REAL,
                    plan_json TEXT NOT NULL,
                    verification_json TEXT NOT NULL,
                    error_message TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS task_steps (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    step_index INTEGER NOT NULL,
                    action TEXT NOT NULL,
                    parameters_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    result TEXT,
                    duration_ms INTEGER,
                    FOREIGN KEY(task_id) REFERENCES tasks(task_id)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    event_type TEXT NOT NULL,
                    details TEXT NOT NULL,
                    severity TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS saved_workflows (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    steps_json TEXT NOT NULL,
                    created_at REAL NOT NULL
                )
            """)
            conn.commit()

    def save_task(self, task: Optional[TaskRecord] = None, **kwargs: Any) -> None:
        """Insert or replace a task record either via TaskRecord or keyword arguments."""
        if task is None:
            task = TaskRecord(
                task_id=kwargs.get("task_id", ""),
                transcript=kwargs.get("transcript", ""),
                objective=kwargs.get("objective", kwargs.get("transcript", "")),
                status=kwargs.get("status", "running"),
                start_time=kwargs.get("start_time", time.time()),
                end_time=kwargs.get("end_time"),
                plan_json=json.dumps(kwargs.get("plan", [])),
                verification_json=json.dumps(kwargs.get("verification", {})),
                error_message=kwargs.get("error_msg") or kwargs.get("error_message"),
            )
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO tasks (
                    task_id, transcript, objective, status, start_time,
                    end_time, plan_json, verification_json, error_message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                task.task_id, task.transcript, task.objective, task.status,
                task.start_time, task.end_time, task.plan_json,
                task.verification_json, task.error_message
            ))
            conn.commit()

    def update_task_status(
        self,
        task_id: str,
        status: str,
        completed_steps: int = 0,
        error_msg: Optional[str] = None,
    ) -> None:
        """Update existing task status and completion details."""
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE tasks
                SET status = ?, end_time = ?, error_message = ?
                WHERE task_id = ?
            """, (status, time.time(), error_msg, task_id))
            conn.commit()

    def save_step(self, step: Optional[StepRecord] = None, **kwargs: Any) -> None:
        """Record an executed step either via StepRecord or keyword arguments."""
        if step is None:
            step = StepRecord(
                task_id=kwargs.get("task_id", ""),
                step_index=kwargs.get("step_index", 0),
                action=kwargs.get("action", ""),
                parameters_json=json.dumps(kwargs.get("parameters", {})),
                status=kwargs.get("status", "completed"),
                result=str(kwargs.get("result", "")),
                duration_ms=kwargs.get("duration_ms", 0),
            )
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO task_steps (
                    task_id, step_index, action, parameters_json,
                    status, result, duration_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                step.task_id, step.step_index, step.action, step.parameters_json,
                step.status, step.result, step.duration_ms
            ))
            conn.commit()

    def get_recent_tasks(self, limit: int = 50) -> list[dict[str, Any]]:
        """Fetch list of recent tasks as dictionaries."""
        with self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM tasks ORDER BY start_time DESC LIMIT ?", (limit,)).fetchall()
            return [dict(r) for r in rows]

    def log_audit(self, event_type: str, details: str, severity: str = "INFO") -> None:
        """Write a security or execution audit log."""
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO audit_logs (timestamp, event_type, details, severity)
                VALUES (?, ?, ?, ?)
            """, (time.time(), event_type, details, severity))
            conn.commit()

    def get_task(self, task_id: str) -> Optional[TaskRecord]:
        """Fetch task by ID."""
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,)).fetchone()
            if not row:
                return None
            return TaskRecord(**dict(row))

    def list_tasks(self, limit: int = 50) -> list[TaskRecord]:
        """List recent tasks."""
        with self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM tasks ORDER BY start_time DESC LIMIT ?", (limit,)).fetchall()
            return [TaskRecord(**dict(r)) for r in rows]

    def delete_task(self, task_id: str) -> bool:
        """Delete task and related steps."""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM task_steps WHERE task_id = ?", (task_id,))
            cursor = conn.execute("DELETE FROM tasks WHERE task_id = ?", (task_id,))
            conn.commit()
            return cursor.rowcount > 0
