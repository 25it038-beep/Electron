"""Task extraction, deadline tracking, deduplication, and scheduling."""

from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Any, Dict, List, Optional
import uuid

from electorn.assistant.schema import ExtractedTask, TaskPriority, TaskStatus


class TaskEngine:
    """Extracts, maintains, deduplicates, and manages tasks from communications and files."""

    def extract_tasks_from_text(self, text: str, source_type: str = "message", source_id: str = "") -> List[ExtractedTask]:
        """Parse natural communication text for actionable commitments, deadlines, and todos."""
        if not text:
            return []

        tasks: List[ExtractedTask] = []
        lines = [line.strip() for line in text.split("\n") if line.strip()]

        task_patterns = [
            r"^(?:todo|task|action item)[:\-]?\s*(.+)",
            r"(?:^|[\.\,\s])(?:todo|task|action item)[:\-]\s*(.+)",
            r"^(?:please\s+ensure|please|kindly|make sure to)\s+(.+)",
            r"(?:urgent|critical)[:\-]\s*(.+)",
            r"(?:must|need to|should|will)\s+([^\.\n]{10,120})",
        ]

        deadline_pattern = r"\b(?:by|due|before|deadline|on)\s+([A-Za-z]+\s+\d{1,2}(?:st|nd|rd|th)?|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b"

        for line in lines:
            for pat in task_patterns:
                m = re.search(pat, line, re.IGNORECASE)
                if m:
                    raw_title = m.group(1).strip()
                    # Clean punctuation
                    clean_title = re.sub(r"[\*#`]", "", raw_title).rstrip(".")
                    if len(clean_title) >= 6:
                        # Extract deadline if present
                        dl_match = re.search(deadline_pattern, line, re.IGNORECASE)
                        deadline = dl_match.group(1).strip() if dl_match else None

                        # Estimate priority
                        priority = TaskPriority.MEDIUM
                        if any(w in line.lower() for w in ("asap", "urgent", "critical", "immediately", "today")):
                            priority = TaskPriority.CRITICAL
                        elif any(w in line.lower() for w in ("important", "high priority", "soon")):
                            priority = TaskPriority.HIGH
                        elif any(w in line.lower() for w in ("optional", "when possible", "low priority")):
                            priority = TaskPriority.LOW

                        tasks.append(
                            ExtractedTask(
                                task_id=f"tsk-{uuid.uuid4().hex[:8]}",
                                title=clean_title[:100],
                                description=line,
                                source_type=source_type,
                                source_id=source_id,
                                deadline=deadline,
                                priority=priority,
                            )
                        )
                    break

        return self.deduplicate_tasks(tasks)

    def deduplicate_tasks(self, tasks: List[ExtractedTask]) -> List[ExtractedTask]:
        """Eliminate redundant or duplicate tasks using title normalization."""
        seen: Dict[str, ExtractedTask] = {}
        for t in tasks:
            norm_key = re.sub(r"\W+", " ", t.title.lower()).strip()
            if norm_key not in seen:
                seen[norm_key] = t
            else:
                # Merge higher priority or more specific deadline
                existing = seen[norm_key]
                if t.priority in (TaskPriority.CRITICAL, TaskPriority.HIGH):
                    existing.priority = t.priority
                if t.deadline and not existing.deadline:
                    existing.deadline = t.deadline
        return list(seen.values())

    def generate_daily_digest(self, tasks: List[ExtractedTask]) -> Dict[str, Any]:
        """Synthesize daily task digest grouped by urgency."""
        pending = [t for t in tasks if t.status == TaskStatus.PENDING]
        critical = [t for t in pending if t.priority == TaskPriority.CRITICAL]
        high = [t for t in pending if t.priority == TaskPriority.HIGH]
        medium_or_low = [t for t in pending if t.priority in (TaskPriority.MEDIUM, TaskPriority.LOW)]

        return {
            "total_pending": len(pending),
            "critical_count": len(critical),
            "high_count": len(high),
            "critical_tasks": [t.title for t in critical],
            "high_tasks": [t.title for t in high],
            "upcoming_tasks": [t.title for t in medium_or_low[:5]],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
