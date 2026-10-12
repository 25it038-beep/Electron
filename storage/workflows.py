"""Workflow template persistence and pre-built multi-step workflows."""

from __future__ import annotations

import json
import time
import uuid
from typing import Any, Optional

from storage.database import TaskDatabase


class WorkflowManager:
    """Manages saved, reusable multi-step automation workflows."""

    def __init__(self, db: TaskDatabase) -> None:
        self.db = db
        self._seed_default_workflows()

    def _seed_default_workflows(self) -> None:
        """Seed foundational combined OS + Browser workflows if database is fresh."""
        existing = self.list_workflows()
        if existing:
            return

        defaults = [
            {
                "id": "wf_research_and_spreadsheet",
                "name": "Research Topic & Save Spreadsheet",
                "description": "Searches for topics on the web, extracts structured info, creates a CSV file, and opens it.",
                "steps": [
                    {"action": "browser.search", "parameters": {"query": "Top AI Conferences 2026"}},
                    {"action": "browser.extract_table", "parameters": {}},
                    {"action": "file.create_file", "parameters": {"path": "Desktop/AI_Conferences.csv", "content": "Conference,Date,Location\nNeurIPS,Dec 2026,Vancouver\nICML,Jul 2026,Seoul\nCVPR,Jun 2026,Seattle"}},
                    {"action": "file.open_path", "parameters": {"path": "Desktop/AI_Conferences.csv"}},
                ],
            },
            {
                "id": "wf_college_assignment",
                "name": "College Portal & Organize Assignment",
                "description": "Opens portal, downloads assignment, creates subject folder on desktop, and saves it.",
                "steps": [
                    {"action": "browser.open_url", "parameters": {"url": "https://example.com/portal/assignments"}},
                    {"action": "file.create_folder", "parameters": {"path": "Desktop/DBMS Records"}},
                    {"action": "file.open_path", "parameters": {"path": "Desktop/DBMS Records"}},
                ],
            },
            {
                "id": "wf_python_project_and_test",
                "name": "Create Python Project & Run Tests",
                "description": "Creates a calculator Python project, runs tests via process runner, and verifies output.",
                "steps": [
                    {"action": "file.create_folder", "parameters": {"path": "Desktop/CalculatorProject"}},
                    {"action": "file.create_file", "parameters": {"path": "Desktop/CalculatorProject/calc.py", "content": "def add(a, b): return a + b\ndef sub(a, b): return a - b\n"}},
                    {"action": "file.create_file", "parameters": {"path": "Desktop/CalculatorProject/test_calc.py", "content": "from calc import add\nassert add(2, 3) == 5\nprint('All tests passed!')\n"}},
                    {"action": "process.run_command", "parameters": {"command": "python test_calc.py", "cwd": "Desktop/CalculatorProject"}},
                ],
            },
        ]

        for wf in defaults:
            self.save_workflow(wf["name"], wf["description"], wf["steps"], wf_id=wf["id"])

    def save_workflow(
        self,
        name: str,
        description: str,
        steps: list[dict[str, Any]],
        wf_id: Optional[str] = None,
    ) -> str:
        """Save a new workflow template."""
        target_id = wf_id or f"wf_{uuid.uuid4().hex[:8]}"
        with self.db._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO saved_workflows (id, name, description, steps_json, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (target_id, name, description, json.dumps(steps), time.time()))
            conn.commit()
        return target_id

    def list_workflows(self) -> list[dict[str, Any]]:
        """List all saved workflows."""
        with self.db._get_connection() as conn:
            rows = conn.execute("SELECT * FROM saved_workflows ORDER BY created_at DESC").fetchall()
            results = []
            for r in rows:
                steps = []
                try:
                    steps = json.loads(r["steps_json"])
                except Exception:
                    pass
                results.append({
                    "id": r["id"],
                    "name": r["name"],
                    "description": r["description"],
                    "steps": steps,
                    "created_at": r["created_at"],
                })
            return results

    def get_workflow(self, wf_id: str) -> Optional[dict[str, Any]]:
        """Fetch workflow by ID."""
        with self.db._get_connection() as conn:
            row = conn.execute("SELECT * FROM saved_workflows WHERE id = ?", (wf_id,)).fetchone()
            if not row:
                return None
            steps = []
            try:
                steps = json.loads(row["steps_json"])
            except Exception:
                pass
            return {
                "id": row["id"],
                "name": row["name"],
                "description": row["description"],
                "steps": steps,
                "created_at": row["created_at"],
            }
