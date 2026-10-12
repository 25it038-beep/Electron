"""Deterministic and LLM-powered multi-step task planning engine."""

from __future__ import annotations

import json
import os
import re
from typing import Any, Optional

from agent.action_schema import TaskPlan, TaskStep
from config.permissions import PermissionLevel, PermissionManager
from providers.base import BaseLLMProvider


class TaskPlanner:
    """Creates structured multi-step TaskPlan instances from natural language commands.
    
    Operates with deterministic parsing (zero-cloud/zero-token offline capability)
    and falls back to / enhances with LLM reasoning when an LLM provider is available.
    """

    def __init__(
        self,
        llm_provider: Optional[BaseLLMProvider] = None,
        permission_engine: Optional[PermissionManager] = None,
    ) -> None:
        self.llm = llm_provider
        self.permissions = permission_engine or PermissionManager()

    def plan(self, user_command: str) -> TaskPlan:
        """Parse natural language command and construct a structured TaskPlan."""
        command = user_command.strip()
        plan = TaskPlan(
            original_transcript=command,
            objective=f"Execute: {command}",
        )

        # 1. Try deterministic rule-based planner first (instant, 100% offline)
        steps = self._plan_deterministic(command)

        # 2. If deterministic pattern matches nothing or is simple, and LLM is available, query LLM
        if (not steps or len(steps) == 0) and self.llm and self.llm.is_available():
            try:
                llm_steps = self._plan_with_llm(command)
                if llm_steps:
                    steps = llm_steps
            except Exception:
                pass

        # 3. If still no steps parsed, generate fallback informational or search step
        if not steps:
            steps = self._fallback_plan(command)

        # 4. Assess risk and attach to plan
        for step in steps:
            risk = self.permissions.check_action(step.action, step.parameters)
            step.risk_level = risk
            step.requires_confirmation = (risk == PermissionLevel.LEVEL_2_CONFIRM)

        plan.steps = steps
        plan.status = "planned"
        return plan

    def _plan_deterministic(self, text: str) -> list[TaskStep]:
        """Recognize composite and single commands using robust regex and semantic templates."""
        t = text.lower()
        steps: list[TaskStep] = []

        # Complex workflow: "open chrome/browser, go to <url>, download/save <file>, create folder <folder>, save there"
        # Check for multi-clause connectors ("and then", "and", "then", ",")
        clauses = re.split(r",\s*and\s*|\s+and\s+then\s+|\s+and\s+|\s+then\s+|;\s*", text, flags=re.IGNORECASE)

        for clause in clauses:
            clause = clause.strip()
            if not clause:
                continue
            sub_step = self._parse_single_clause(clause)
            if sub_step:
                steps.append(sub_step)

        return steps

    def _parse_single_clause(self, clause: str) -> Optional[TaskStep]:
        c = clause.strip()
        cl = c.lower()

        # Browser URL / Navigate
        if cl.startswith("open url ") or cl.startswith("go to ") or cl.startswith("browse to "):
            url = re.sub(r"^(open url|go to|browse to)\s+", "", c, flags=re.IGNORECASE).strip()
            if not url.startswith("http://") and not url.startswith("https://"):
                url = f"https://{url}"
            return TaskStep(
                action="browser.open_url",
                parameters={"url": url},
                description=f"Navigate browser to {url}",
            )

        # Browser Search
        if cl.startswith("search ") or cl.startswith("google ") or "search for " in cl:
            query = re.sub(r"^(search for|search|google)\s+", "", c, flags=re.IGNORECASE).strip()
            return TaskStep(
                action="browser.search",
                parameters={"query": query},
                description=f"Search Google for '{query}'",
            )

        # Browser Extract / Export CSV
        if "extract table" in cl or "save table" in cl or "export table" in cl or "export to csv" in cl or "save as csv" in cl:
            m = re.search(r"(?:to|as)\s+([a-zA-Z0-9_\-\./\\]+\.csv)", c, re.IGNORECASE)
            csv_path = m.group(1) if m else os.path.expanduser("~/Desktop/table_export.csv")
            return TaskStep(
                action="browser.export_csv",
                parameters={"file_path": csv_path},
                description=f"Extract webpage table to CSV at {csv_path}",
            )

        # Browser screenshot
        if "screenshot" in cl or "capture screen" in cl:
            filename = os.path.expanduser(f"~/Desktop/screenshot_{int(os.getpid())}.png")
            return TaskStep(
                action="browser.screenshot",
                parameters={"filename": filename},
                description=f"Capture screenshot to {filename}",
            )

        # Browser close
        if "close browser" in cl or "quit browser" in cl or "exit browser" in cl:
            return TaskStep(
                action="browser.close",
                parameters={},
                description="Close browser session",
            )

        # OS App Launch
        if cl.startswith("open ") or cl.startswith("launch ") or cl.startswith("start "):
            target = re.sub(r"^(open|launch|start)\s+", "", c, flags=re.IGNORECASE).strip()
            # If target looks like a website (has .com, .org, etc.), route to browser
            if any(target.endswith(ext) for ext in [".com", ".org", ".io", ".edu", ".net", ".in", ".gov"]):
                url = f"https://{target}" if not target.startswith("http") else target
                return TaskStep(action="browser.open_url", parameters={"url": url}, description=f"Open {url}")
            return TaskStep(
                action="os.launch_app",
                parameters={"app": target},
                description=f"Launch application '{target}'",
            )

        # OS App Close
        if cl.startswith("close app ") or cl.startswith("terminate ") or cl.startswith("kill app "):
            target = re.sub(r"^(close app|terminate|kill app|close)\s+", "", c, flags=re.IGNORECASE).strip()
            return TaskStep(
                action="os.close_app",
                parameters={"app": target},
                description=f"Close application '{target}'",
            )

        # File Create Folder
        if "create a folder" in cl or "create folder" in cl or "make a folder" in cl or "make directory" in cl:
            folder_match = re.search(r"(?:folder|directory)(?:\s+called|\s+named)?\s+['\"]?([^'\"\n]+?)['\"]?(?:\s+on|\s+in|$)", c, re.IGNORECASE)
            folder_name = folder_match.group(1).strip() if folder_match else "New Folder"
            loc = "desktop" if "desktop" in cl else "documents" if "documents" in cl else ""
            if loc == "desktop":
                target_path = os.path.expanduser(f"~/Desktop/{folder_name}")
            elif loc == "documents":
                target_path = os.path.expanduser(f"~/Documents/{folder_name}")
            else:
                target_path = os.path.expanduser(f"~/{folder_name}")

            return TaskStep(
                action="file.create_folder",
                parameters={"path": target_path},
                description=f"Create directory '{target_path}'",
            )

        # File Create File / Note
        if "create a file" in cl or "create file" in cl or "write file" in cl or "save note" in cl:
            path = os.path.expanduser("~/Desktop/electorn_note.txt")
            return TaskStep(
                action="file.create_file",
                parameters={"path": path, "content": "Created by Electorn AI Automated Workflow.\n"},
                description=f"Create file at {path}",
            )

        # File Organize Files
        if "organize" in cl and ("file" in cl or "files" in cl):
            ext = ".pdf" if "pdf" in cl else ".png" if "image" in cl or "png" in cl else ".txt"
            src = os.path.expanduser("~/Downloads")
            dst = os.path.expanduser(f"~/Downloads/{ext.replace('.', '').upper()}_Files")
            return TaskStep(
                action="file.organize_files",
                parameters={"source_dir": src, "target_dir": dst, "ext": ext},
                description=f"Organize {ext} files from {src} into {dst}",
            )

        # OS System Specs / Battery / CPU
        if any(k in cl for k in ["system specs", "battery", "cpu", "ram", "memory usage", "disk space", "system info"]):
            return TaskStep(
                action="os.system_specs",
                parameters={},
                description="Inspect system hardware specs, CPU, RAM, Disk, and Battery",
            )

        # Volume / Media
        if "volume up" in cl or "increase volume" in cl:
            return TaskStep(action="os.volume", parameters={"action": "up"}, description="Increase audio volume")
        if "volume down" in cl or "decrease volume" in cl:
            return TaskStep(action="os.volume", parameters={"action": "down"}, description="Decrease audio volume")
        if "mute" in cl or "unmute" in cl:
            return TaskStep(action="os.volume", parameters={"action": "mute"}, description="Toggle audio mute")
        if "pause music" in cl or "pause media" in cl or "play music" in cl or "resume media" in cl:
            return TaskStep(action="os.media", parameters={"action": "play_pause"}, description="Toggle media playback")

        # Windows Navigation
        if "minimize" in cl or "show desktop" in cl:
            return TaskStep(action="os.minimize_windows", parameters={}, description="Minimize all windows to desktop")
        if "maximize" in cl:
            return TaskStep(action="os.maximize_window", parameters={}, description="Maximize active window")
        if "switch window" in cl or "next window" in cl:
            return TaskStep(action="os.switch_window", parameters={}, description="Switch active window")
        if "lock" in cl and ("computer" in cl or "pc" in cl or "screen" in cl or "workstation" in cl):
            return TaskStep(action="os.lock", parameters={}, description="Lock Windows workstation")

        return None

    def _plan_with_llm(self, command: str) -> list[TaskStep]:
        """Ask LLM to produce JSON action plan."""
        prompt = (
            f"Generate a validated JSON list of steps for command: '{command}'.\n"
            f"Allowed actions: browser.open_url, browser.search, browser.click, browser.type, "
            f"browser.extract_table, browser.export_csv, browser.screenshot, browser.close, "
            f"os.launch_app, os.close_app, os.minimize_windows, os.maximize_window, os.volume, "
            f"os.system_specs, file.create_folder, file.create_file, file.move_file, file.copy_file.\n"
            f"Respond ONLY with a JSON array: [{{\"action\": \"...\", \"parameters\": {{...}}, \"description\": \"...\"}}]"
        )
        response_text = self.llm.ask(prompt)
        match = re.search(r"\[\s*\{.*\}\s*\]", response_text, re.DOTALL)
        if not match:
            return []

        raw_list = json.loads(match.group(0))
        steps = []
        for item in raw_list:
            if "action" in item:
                steps.append(
                    TaskStep(
                        action=item["action"],
                        parameters=item.get("parameters", {}),
                        description=item.get("description", item["action"]),
                    )
                )
        return steps

    def _fallback_plan(self, command: str) -> list[TaskStep]:
        """Fallback: if text is query-like, search it; otherwise inspect system specs."""
        if len(command.split()) > 1:
            return [
                TaskStep(
                    action="browser.search",
                    parameters={"query": command},
                    description=f"Search Google for '{command}'",
                )
            ]
        return [
            TaskStep(
                action="os.system_specs",
                parameters={},
                description="Query system status and specs",
            )
        ]
