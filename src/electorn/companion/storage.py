"""Configuration persistence and activity audit logging for Companion Mode."""

from __future__ import annotations

import json
from pathlib import Path
import threading
import time
from typing import Any, Dict, List, Optional

from electorn.companion.schema import CompanionConfig, CompanionMode


class CompanionStorage:
    """Manages companion configuration and persistent JSONL activity audit logs."""

    def __init__(self, base_dir: Optional[Path] = None) -> None:
        self.base_dir = base_dir or (Path.home() / ".electorn" / "companion")
        self.config_file = self.base_dir / "config.json"
        self.activity_file = self.base_dir / "activity.jsonl"
        self._lock = threading.Lock()
        self._ensure_storage()

    def _ensure_storage(self) -> None:
        """Create storage directory if not present."""
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def load_config(self) -> CompanionConfig:
        """Load configuration from disk or initialize defaults."""
        with self._lock:
            if not self.config_file.exists():
                cfg = CompanionConfig()
                self._save_config_unlocked(cfg)
                return cfg

            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return CompanionConfig(**data)
            except Exception:
                return CompanionConfig()

    def save_config(self, config: CompanionConfig) -> None:
        """Persist companion configuration."""
        with self._lock:
            self._save_config_unlocked(config)

    def _save_config_unlocked(self, config: CompanionConfig) -> None:
        """Internal helper to write config to file."""
        temp_file = self.config_file.with_suffix(".tmp")
        with open(temp_file, "w", encoding="utf-8") as f:
            f.write(config.model_dump_json(indent=2))
        temp_file.replace(self.config_file)

    def reset_config(self) -> CompanionConfig:
        """Reset companion settings to fresh default state."""
        cfg = CompanionConfig()
        self.save_config(cfg)
        return cfg

    def log_activity(self, activity_type: str, details: Dict[str, Any]) -> None:
        """Append an entry to the audit log."""
        record = {
            "timestamp": time.time(),
            "type": activity_type,
            "details": details,
        }
        with self._lock:
            try:
                with open(self.activity_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps(record) + "\n")
            except Exception:
                pass

    def load_recent_activity(self, limit: int = 30) -> List[Dict[str, Any]]:
        """Read recent activity log records."""
        with self._lock:
            if not self.activity_file.exists():
                return []
            try:
                lines = []
                with open(self.activity_file, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                records = []
                for line in reversed(lines):
                    line = line.strip()
                    if line:
                        try:
                            records.append(json.loads(line))
                            if len(records) >= limit:
                                break
                        except Exception:
                            continue
                return records
            except Exception:
                return []

    def clear_activity(self) -> None:
        """Clear the activity log file."""
        with self._lock:
            if self.activity_file.exists():
                try:
                    self.activity_file.unlink()
                except Exception:
                    pass
