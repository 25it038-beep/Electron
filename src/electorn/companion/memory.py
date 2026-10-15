"""Persistent memory manager for Electorn Companion Mode."""

from __future__ import annotations

import json
from pathlib import Path
import re
import threading
import time
from typing import Dict, List, Optional
import uuid

from electorn.companion.schema import CompanionMemoryItem, MemoryCategory


class MemoryEngine:
    """Thread-safe persistent memory manager storing user preferences, projects, and facts."""

    def __init__(self, storage_dir: Optional[Path] = None) -> None:
        self.storage_dir = storage_dir or (Path.home() / ".electorn" / "companion")
        self.memory_file = self.storage_dir / "memory.json"
        self._lock = threading.Lock()
        self._ensure_storage()

    def _ensure_storage(self) -> None:
        """Create storage directory and initial memory file if missing."""
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        if not self.memory_file.exists():
            with open(self.memory_file, "w", encoding="utf-8") as f:
                json.dump([], f, indent=2)

    def load_all(self) -> List[CompanionMemoryItem]:
        """Load all memory items from disk."""
        with self._lock:
            if not self.memory_file.exists():
                return []
            try:
                with open(self.memory_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return [CompanionMemoryItem(**item) for item in data]
            except Exception:
                return []

    def _save_all(self, items: List[CompanionMemoryItem]) -> None:
        """Persist items to disk atomically."""
        with self._lock:
            temp_file = self.memory_file.with_suffix(".tmp")
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump([item.model_dump() for item in items], f, indent=2)
            temp_file.replace(self.memory_file)

    def add_memory(
        self,
        category: MemoryCategory,
        key: str,
        value: str,
        confidence: float = 1.0,
        source: str = "conversation",
    ) -> CompanionMemoryItem:
        """Add or update a memory record."""
        items = self.load_all()
        # Deduplicate or update existing item with identical key and category
        clean_key = key.strip().lower()
        existing = next((i for i in items if i.category == category and i.key.strip().lower() == clean_key), None)

        if existing:
            existing.value = value.strip()
            existing.timestamp = time.time()
            existing.confidence = confidence
            existing.source = source
            self._save_all(items)
            return existing

        new_item = CompanionMemoryItem(
            memory_id=f"mem-{uuid.uuid4().hex[:8]}",
            timestamp=time.time(),
            category=category,
            key=key.strip(),
            value=value.strip(),
            confidence=confidence,
            source=source,
        )
        items.append(new_item)
        self._save_all(items)
        return new_item

    def get_memories(self, category: Optional[MemoryCategory] = None) -> List[CompanionMemoryItem]:
        """Retrieve memory records, optionally filtered by category."""
        items = self.load_all()
        if category:
            return [i for i in items if i.category == category]
        return items

    def search_memories(self, query: str) -> List[CompanionMemoryItem]:
        """Fuzzy keyword search over memory keys and values."""
        q = query.strip().lower()
        items = self.load_all()
        return [i for i in items if q in i.key.lower() or q in i.value.lower()]

    def delete_memory(self, memory_id: str) -> bool:
        """Delete a memory record by ID."""
        items = self.load_all()
        filtered = [i for i in items if i.memory_id != memory_id]
        if len(filtered) < len(items):
            self._save_all(filtered)
            return True
        return False

    def clear_memories(self) -> None:
        """Wipe all stored memories (privacy action)."""
        self._save_all([])

    def extract_and_remember(self, user_text: str) -> List[CompanionMemoryItem]:
        """Automatically identify and preserve user preferences, active projects, or stated habits."""
        if not user_text:
            return []

        learned: List[CompanionMemoryItem] = []
        text = user_text.strip()

        # Preference patterns (e.g. "I love...", "I prefer...", "My favorite...")
        pref_patterns = [
            r"\b(?:i like|i prefer|i love|my preference is)\s+([^\.\n,]{3,60})",
            r"\b(?:i don't like|i dislike|i hate)\s+([^\.\n,]{3,60})",
        ]
        for pat in pref_patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                pref = m.group(1).strip()
                item = self.add_memory(
                    category=MemoryCategory.USER_PREFERENCE,
                    key=f"preference_{pref[:20]}",
                    value=f"Prefers: {pref}",
                    source="conversation",
                )
                learned.append(item)

        # Active project patterns (e.g. "I am working on...", "Project is...")
        proj_patterns = [
            r"\b(?:working on|building|developing|project is)\s+([A-Za-z0-9_\-]{3,40})",
        ]
        for pat in proj_patterns:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                proj_name = m.group(1).strip()
                item = self.add_memory(
                    category=MemoryCategory.ACTIVE_PROJECT,
                    key="active_project",
                    value=proj_name,
                    source="conversation",
                )
                learned.append(item)

        return learned

    def get_prompt_context(self, limit: int = 8) -> List[str]:
        """Format persistent memories into concise strings for prompt injection."""
        items = self.load_all()
        # Sort by most recent
        items.sort(key=lambda x: x.timestamp, reverse=True)
        recent_items = items[:limit]

        context_lines: List[str] = []
        for item in recent_items:
            if item.category == MemoryCategory.USER_PREFERENCE:
                context_lines.append(f"Preference: {item.value}")
            elif item.category == MemoryCategory.ACTIVE_PROJECT:
                context_lines.append(f"Current Project: {item.value}")
            elif item.category == MemoryCategory.TASK_COMMITMENT:
                context_lines.append(f"Task: {item.value}")
            elif item.category == MemoryCategory.OBSERVED_WORK_STYLE:
                context_lines.append(f"Work style: {item.value}")
            else:
                context_lines.append(f"{item.key}: {item.value}")
        return context_lines
