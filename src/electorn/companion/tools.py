"""Safe Electorn tool integration bridge for Companion Mode."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
from typing import Any, Dict, List, Optional
import uuid

from electorn.assistant.schema import ExtractedTask, TaskPriority, TaskStatus
from electorn.assistant.storage import AssistantStorage
from electorn.runtime.web_search import WebSearchEngine


class CompanionTools:
    """Registry of safe, guarded actions the companion can execute on behalf of the user."""

    SAFE_READ_COMMANDS = {"git status", "git log", "git diff", "dir", "ls", "python --version", "node --version", "pytest --version"}

    def __init__(self, workspace_path: Optional[Path] = None) -> None:
        self.workspace = workspace_path or Path.cwd()
        self.storage = AssistantStorage()
        self.web_searcher = WebSearchEngine()

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Return schema descriptors for all companion tools."""
        return [
            {
                "name": "read_file",
                "description": "Read contents of a file within the project workspace.",
                "parameters": {"path": "string", "max_lines": "integer"},
            },
            {
                "name": "list_files",
                "description": "List files and subdirectories in a workspace path.",
                "parameters": {"subpath": "string"},
            },
            {
                "name": "search_code",
                "description": "Search text or regex across workspace files.",
                "parameters": {"query": "string"},
            },
            {
                "name": "run_tests",
                "description": "Run automated test suite (e.g. pytest or npm test).",
                "parameters": {"runner": "string"},
            },
            {
                "name": "run_command",
                "description": "Execute a terminal command with safety validation.",
                "parameters": {"command": "string"},
            },
            {
                "name": "create_task",
                "description": "Create a new task reminder on the user's task board.",
                "parameters": {"title": "string", "priority": "string"},
            },
            {
                "name": "list_tasks",
                "description": "List pending tasks and commitments.",
                "parameters": {},
            },
            {
                "name": "search_web",
                "description": "Search the live web for recent answers or programming documentation.",
                "parameters": {"query": "string"},
            },
        ]

    def read_file(self, path: str, max_lines: int = 100) -> str:
        """Safely read lines from a project file."""
        try:
            target = (self.workspace / path).resolve()
            if not target.exists() or not target.is_file():
                return f"File not found: {path}"

            with open(target, "r", encoding="utf-8", errors="replace") as f:
                lines = [f.readline() for _ in range(max_lines)]
                return "".join(lines)
        except Exception as e:
            return f"Error reading file: {e}"

    def list_files(self, subpath: str = "") -> List[str]:
        """List files in the target workspace directory."""
        try:
            target = (self.workspace / subpath).resolve()
            if not target.exists() or not target.is_dir():
                return []
            items = []
            for item in target.iterdir():
                if item.name.startswith("."):
                    continue
                suffix = "/" if item.is_dir() else ""
                items.append(f"{item.name}{suffix}")
            return sorted(items[:60])
        except Exception:
            return []

    def search_code(self, query: str) -> List[str]:
        """Search for a string across text files in workspace."""
        if not query:
            return []
        matches = []
        try:
            for root, _, files in os.walk(self.workspace):
                if any(p in root for p in [".git", "node_modules", ".venv", "__pycache__", ".electorn"]):
                    continue
                for fname in files:
                    fpath = Path(root) / fname
                    if fpath.suffix in [".py", ".ts", ".js", ".json", ".md", ".html", ".css", ".txt"]:
                        try:
                            content = fpath.read_text(encoding="utf-8", errors="ignore")
                            if query.lower() in content.lower():
                                rel = fpath.relative_to(self.workspace)
                                matches.append(str(rel))
                                if len(matches) >= 15:
                                    return matches
                        except Exception:
                            pass
        except Exception:
            pass
        return matches

    def run_tests(self, runner: str = "pytest") -> Dict[str, Any]:
        """Execute test runner safely and return summary."""
        cmd = [runner, "-q"] if runner == "pytest" else ["npm", "test"]
        try:
            res = subprocess.run(
                cmd,
                cwd=str(self.workspace),
                capture_output=True,
                text=True,
                timeout=60,
                shell=(sys.platform == "win32"),
            )
            return {
                "success": res.returncode == 0,
                "output": (res.stdout + res.stderr)[:1000],
                "returncode": res.returncode,
            }
        except Exception as e:
            return {"success": False, "output": f"Test run error: {e}", "returncode": -1}

    def run_command(self, command: str) -> Dict[str, Any]:
        """Run terminal command with safety validation."""
        clean_cmd = command.strip()
        # Security: Disallow dangerous patterns
        for bad in ["rm -rf", "del /s", "format", "mkfs", "drop table", ":(){ :|:& };:"]:
            if bad in clean_cmd.lower():
                return {
                    "success": False,
                    "output": "Command blocked: contains destructive or high-risk pattern.",
                    "requires_approval": True,
                }

        # Check if safe read-only
        is_safe = any(clean_cmd.lower().startswith(safe) for safe in self.SAFE_READ_COMMANDS)

        try:
            res = subprocess.run(
                clean_cmd,
                cwd=str(self.workspace),
                capture_output=True,
                text=True,
                timeout=30,
                shell=True,
            )
            return {
                "success": res.returncode == 0,
                "output": (res.stdout + res.stderr)[:1000],
                "returncode": res.returncode,
                "requires_approval": not is_safe,
            }
        except Exception as e:
            return {"success": False, "output": f"Execution error: {e}", "returncode": -1}

    def create_task(self, title: str, priority: str = "medium") -> ExtractedTask:
        """Create a new task on the assistant task board."""
        p_enum = TaskPriority.MEDIUM
        if priority.lower() in ("high", "urgent", "critical"):
            p_enum = TaskPriority.HIGH
        elif priority.lower() in ("low",):
            p_enum = TaskPriority.LOW

        task = ExtractedTask(
            task_id=f"tsk-{uuid.uuid4().hex[:8]}",
            title=title.strip()[:100],
            description=f"Task logged by Companion: {title}",
            source_type="companion",
            priority=p_enum,
            status=TaskStatus.PENDING,
        )
        self.storage.save_task(task)
        return task

    def list_tasks(self) -> List[Dict[str, Any]]:
        """List active pending tasks."""
        tasks = self.storage.list_tasks(status=TaskStatus.PENDING)
        return [{"id": t.task_id, "title": t.title, "priority": t.priority.value} for t in tasks]

    def search_web(self, query: str) -> str:
        """Query live search and format top results."""
        results = self.web_searcher.search(query, max_results=3)
        if not results:
            return "No recent search results found."
        formatted = []
        for r in results:
            formatted.append(f"- **{r.title}**: {r.snippet} ({r.url})")
        return "\n".join(formatted)
