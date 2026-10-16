"""Proactive Web Research & Scheduled Information Monitoring Engine for Electorn AI.

Continuously monitors configured interests (AI models, developer tools, hackathons, papers),
deduplicates findings, ranks relevance, and formulates proactive morning briefings.
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
import re
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from electorn.automation.web_agent import PlaywrightWebAgent

logger = logging.getLogger(__name__)


class MonitoredInterest(BaseModel):
    """A configured user interest domain tracked by the autonomous monitor."""
    topic_id: str
    title: str
    query: str
    enabled: bool = True
    interval_hours: int = 6
    last_checked: float = 0.0

    @property
    def topic(self) -> str:
        return self.title


class DiscoveredItem(BaseModel):
    """A single verified discovery or newly published article/tool."""
    item_id: str = ""
    topic_id: str = "general"
    title: str
    url: str
    snippet: str = ""
    summary: str = ""
    category: str = "general"
    discovered_at: float = Field(default_factory=time.time)
    relevance_score: float = 1.0
    notified: bool = False


class ProactiveResearchMonitor:
    """Discovers, filters, ranks, and notifies the user of fresh real-world developments."""

    DEFAULT_INTERESTS = [
        MonitoredInterest(
            topic_id="ai_models",
            title="AI Models & Open Source LLMs",
            query="new open source LLM model releases GitHub Ollama 2026",
            interval_hours=12,
        ),
        MonitoredInterest(
            topic_id="dev_tools",
            title="Python & AI Developer Tools",
            query="new Python AI frameworks tools release 2026",
            interval_hours=12,
        ),
        MonitoredInterest(
            topic_id="hackathons",
            title="Hackathons & Student Opportunities",
            query="upcoming college AI hackathons student competitions 2026",
            interval_hours=24,
        ),
    ]

    def __init__(self, storage_dir: Optional[Path] = None) -> None:
        self.storage_dir = storage_dir or (Path.home() / ".electorn" / "monitoring")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.interests_file = self.storage_dir / "interests.json"
        self.discoveries_file = self.storage_dir / "discoveries.jsonl"
        self.web_agent = PlaywrightWebAgent()

        self.interests: List[MonitoredInterest] = self._load_interests()
        self.known_hashes: set[str] = self._load_known_hashes()

    def _load_interests(self) -> List[MonitoredInterest]:
        """Load configured interests or initialize defaults."""
        if not self.interests_file.exists():
            self._save_interests(self.DEFAULT_INTERESTS)
            return list(self.DEFAULT_INTERESTS)

        try:
            with open(self.interests_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return [MonitoredInterest(**item) for item in data]
        except Exception:
            return list(self.DEFAULT_INTERESTS)

    def _save_interests(self, items: List[MonitoredInterest]) -> None:
        """Persist interests to disk."""
        try:
            with open(self.interests_file, "w", encoding="utf-8") as f:
                json.dump([item.model_dump() for item in items], f, indent=2)
        except Exception as e:
            logger.debug("Failed saving interests: %s", e)

    def _load_known_hashes(self) -> set[str]:
        """Load hash set of already discovered URLs to prevent duplicates."""
        hashes = set()
        if not self.discoveries_file.exists():
            return hashes

        try:
            with open(self.discoveries_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        obj = json.loads(line)
                        if "item_id" in obj:
                            hashes.add(obj["item_id"])
        except Exception:
            pass
        return hashes

    def _compute_hash(self, url: str) -> str:
        """Compute unique deterministic identifier for a URL."""
        return hashlib.sha256(url.strip().lower().encode("utf-8")).hexdigest()[:16]

    def is_duplicate(self, url: str) -> bool:
        """Check whether a URL has already been recorded and notified."""
        return self._compute_hash(url) in self.known_hashes

    def record_discovery(self, item: DiscoveredItem) -> None:
        """Record and persist a newly discovered item into known set."""
        if not item.item_id:
            item.item_id = self._compute_hash(item.url)
        self.known_hashes.add(item.item_id)
        self._persist_discovery(item)

    def get_active_interests(self) -> List[MonitoredInterest]:
        """Return list of active monitored interests."""
        return [i for i in self.interests if i.enabled]

    def add_interest(
        self,
        topic: str,
        category: str = "general",
        keywords: Optional[List[str]] = None,
        interval_hours: int = 12,
    ) -> MonitoredInterest:
        """Register a new proactive topic interest to track."""
        topic_id = re.sub(r"[^a-z0-9]+", "_", topic.lower()).strip("_")
        query_str = " ".join(keywords or [topic])
        interest = MonitoredInterest(
            topic_id=topic_id,
            title=topic,
            query=query_str,
            interval_hours=interval_hours,
        )
        self.interests.append(interest)
        self._save_interests(self.interests)
        return interest

    # =========================================================================
    # 1. MONITORING EXECUTION & DEDUPLICATION
    # =========================================================================

    def run_monitoring_cycle(self, force: bool = False) -> List[DiscoveredItem]:
        """Check all active interests that are due for an update and gather new discoveries."""
        now = time.time()
        new_discoveries: List[DiscoveredItem] = []

        for interest in self.interests:
            if not interest.enabled:
                continue

            elapsed_hours = (now - interest.last_checked) / 3600.0
            if not force and elapsed_hours < interest.interval_hours:
                continue

            try:
                results = self.web_agent.search_queries(interest.query, max_results=5)
                for res in results:
                    url = res.get("url", "").strip()
                    title = res.get("title", "").strip()
                    if not url or not title:
                        continue

                    item_hash = self._compute_hash(url)
                    if item_hash in self.known_hashes:
                        continue  # Deduplicated

                    # Fresh discovery
                    item = DiscoveredItem(
                        item_id=item_hash,
                        topic_id=interest.topic_id,
                        title=title,
                        url=url,
                        snippet=res.get("snippet", ""),
                        discovered_at=now,
                    )
                    new_discoveries.append(item)
                    self.known_hashes.add(item_hash)
                    self._persist_discovery(item)

                interest.last_checked = now
            except Exception as exc:
                logger.debug("Error monitoring interest '%s': %s", interest.title, exc)

        self._save_interests(self.interests)
        return new_discoveries

    def _persist_discovery(self, item: DiscoveredItem) -> None:
        """Append newly discovered item to the persistent JSONL storage."""
        try:
            with open(self.discoveries_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(item.model_dump()) + "\n")
        except Exception as e:
            logger.debug("Failed writing discovery record: %s", e)

    # =========================================================================
    # 2. BRIEFING FORMULATION
    # =========================================================================

    def get_recent_discoveries(self, limit: int = 5) -> List[DiscoveredItem]:
        """Retrieve most recent discovered items from disk."""
        items: List[DiscoveredItem] = []
        if not self.discoveries_file.exists():
            return items

        try:
            with open(self.discoveries_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        items.append(DiscoveredItem(**json.loads(line)))
        except Exception:
            pass

        items.sort(key=lambda x: x.discovered_at, reverse=True)
        return items[:limit]

    def generate_morning_briefing(self, user_name: str = "Harshan") -> str:
        """Synthesize a personalized morning briefing of fresh discoveries."""
        recent = self.get_recent_discoveries(limit=3)
        if not recent:
            return f"Good morning, {user_name}! [Morning Briefing] Everything is running smoothly. No new priority updates right now."

        lines = [f"Good morning, {user_name}! [Morning Briefing] Here are {len(recent)} fresh updates I found for you:"]
        for i, item in enumerate(recent, start=1):
            lines.append(f"{i}. {item.title} ({item.url})")
        lines.append("Would you like me to open any of these or research them in depth?")
        return "\n".join(lines)
