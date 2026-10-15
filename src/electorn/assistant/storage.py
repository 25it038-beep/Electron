"""Unified repository and persistence store for messages, actions, tasks, and state."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid

from electorn.assistant.schema import (
    ActionItem,
    ActionStatus,
    AssistantConfig,
    CallBriefing,
    CallRecord,
    ChannelType,
    DocumentAnalysisReport,
    ExtractedTask,
    MessageRecord,
    TaskStatus,
)


class AssistantStorage:
    """Persistent JSON / JSONL state engine for the Personal Assistant."""

    def __init__(self, base_dir: Optional[Path] = None) -> None:
        self.base_dir = base_dir or (Path.home() / ".electorn" / "assistant")
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.config_path = self.base_dir / "config.json"
        self.messages_path = self.base_dir / "messages.json"
        self.actions_path = self.base_dir / "actions.json"
        self.tasks_path = self.base_dir / "tasks.json"
        self.calls_path = self.base_dir / "calls.json"
        self.reports_path = self.base_dir / "reports.json"

        self._ensure_files()

    def _ensure_files(self) -> None:
        for p in (self.messages_path, self.actions_path, self.tasks_path, self.calls_path, self.reports_path):
            if not p.exists():
                p.write_text("[]", encoding="utf-8")

    # --- CONFIG ---
    def load_config(self) -> AssistantConfig:
        if self.config_path.exists():
            try:
                data = json.loads(self.config_path.read_text(encoding="utf-8"))
                return AssistantConfig.model_validate(data)
            except Exception:
                pass
        cfg = AssistantConfig()
        self.save_config(cfg)
        return cfg

    def save_config(self, cfg: AssistantConfig) -> None:
        self.config_path.write_text(cfg.model_dump_json(indent=2), encoding="utf-8")

    # --- MESSAGES ---
    def list_messages(self, channel: Optional[ChannelType] = None, limit: int = 50) -> List[MessageRecord]:
        try:
            items = json.loads(self.messages_path.read_text(encoding="utf-8"))
            records = [MessageRecord.model_validate(m) for m in items]
            if channel:
                records = [r for r in records if r.channel == channel]
            return sorted(records, key=lambda x: x.timestamp, reverse=True)[:limit]
        except Exception:
            return []

    def get_message(self, message_id: str) -> Optional[MessageRecord]:
        for m in self.list_messages(limit=500):
            if m.message_id == message_id:
                return m
        return None

    def save_message(self, message: MessageRecord) -> None:
        try:
            items = json.loads(self.messages_path.read_text(encoding="utf-8"))
            # Update existing or append
            updated = False
            for i, it in enumerate(items):
                if it.get("message_id") == message.message_id:
                    items[i] = message.model_dump(mode="json")
                    updated = True
                    break
            if not updated:
                items.append(message.model_dump(mode="json"))
            self.messages_path.write_text(json.dumps(items, indent=2, default=str), encoding="utf-8")
        except Exception:
            pass

    # --- ACTIONS (APPROVALS) ---
    def list_actions(self, status: Optional[ActionStatus] = None) -> List[ActionItem]:
        try:
            items = json.loads(self.actions_path.read_text(encoding="utf-8"))
            actions = [ActionItem.model_validate(a) for a in items]
            if status:
                actions = [a for a in actions if a.status == status]
            return sorted(actions, key=lambda x: x.created_at, reverse=True)
        except Exception:
            return []

    def get_action(self, action_id: str) -> Optional[ActionItem]:
        for a in self.list_actions():
            if a.action_id == action_id:
                return a
        return None

    def save_action(self, action: ActionItem) -> None:
        try:
            items = json.loads(self.actions_path.read_text(encoding="utf-8"))
            updated = False
            for i, it in enumerate(items):
                if it.get("action_id") == action.action_id:
                    items[i] = action.model_dump(mode="json")
                    updated = True
                    break
            if not updated:
                items.append(action.model_dump(mode="json"))
            self.actions_path.write_text(json.dumps(items, indent=2, default=str), encoding="utf-8")
        except Exception:
            pass

    # --- TASKS ---
    def list_tasks(self, status: Optional[TaskStatus] = None) -> List[ExtractedTask]:
        try:
            items = json.loads(self.tasks_path.read_text(encoding="utf-8"))
            tasks = [ExtractedTask.model_validate(t) for t in items]
            if status:
                tasks = [t for t in tasks if t.status == status]
            return sorted(tasks, key=lambda x: x.created_at, reverse=True)
        except Exception:
            return []

    def get_task(self, task_id: str) -> Optional[ExtractedTask]:
        for t in self.list_tasks():
            if t.task_id == task_id:
                return t
        return None

    def save_task(self, task: ExtractedTask) -> None:
        try:
            items = json.loads(self.tasks_path.read_text(encoding="utf-8"))
            updated = False
            for i, it in enumerate(items):
                if it.get("task_id") == task.task_id:
                    items[i] = task.model_dump(mode="json")
                    updated = True
                    break
            if not updated:
                items.append(task.model_dump(mode="json"))
            self.tasks_path.write_text(json.dumps(items, indent=2, default=str), encoding="utf-8")
        except Exception:
            pass

    # --- CALLS ---
    def list_calls(self) -> List[CallRecord]:
        try:
            items = json.loads(self.calls_path.read_text(encoding="utf-8"))
            return [CallRecord.model_validate(c) for c in items]
        except Exception:
            return []

    def get_call(self, call_id: str) -> Optional[CallRecord]:
        for c in self.list_calls():
            if c.call_id == call_id:
                return c
        return None

    def save_call(self, call: CallRecord) -> None:
        try:
            items = json.loads(self.calls_path.read_text(encoding="utf-8"))
            updated = False
            for i, it in enumerate(items):
                if it.get("call_id") == call.call_id:
                    items[i] = call.model_dump(mode="json")
                    updated = True
                    break
            if not updated:
                items.append(call.model_dump(mode="json"))
            self.calls_path.write_text(json.dumps(items, indent=2, default=str), encoding="utf-8")
        except Exception:
            pass

    # --- DOCUMENT REPORTS ---
    def save_report(self, report: DocumentAnalysisReport) -> None:
        try:
            items = json.loads(self.reports_path.read_text(encoding="utf-8"))
            items.append(report.model_dump(mode="json"))
            self.reports_path.write_text(json.dumps(items, indent=2, default=str), encoding="utf-8")
        except Exception:
            pass

    def list_reports(self) -> List[DocumentAnalysisReport]:
        try:
            items = json.loads(self.reports_path.read_text(encoding="utf-8"))
            return [DocumentAnalysisReport.model_validate(r) for r in items]
        except Exception:
            return []
