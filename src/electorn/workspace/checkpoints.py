"""Change management, workspace snapshots, diffs, and rollback engine."""

from __future__ import annotations

import difflib
import json
import os
import shutil
import time
import uuid
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field


class CheckpointMeta(BaseModel):
    """Metadata describing a recorded workspace snapshot."""

    id: str
    timestamp: float
    iso_time: str
    message: str
    files: list[str] = Field(default_factory=list)


class CheckpointManager:
    """Safely manages project snapshots, diffs, and rollbacks within .electorn/checkpoints/."""

    def __init__(self, workspace_root: Path | str, ignore_patterns: Optional[list[str]] = None):
        self.workspace_root = Path(workspace_root).resolve()
        self.checkpoints_dir = self.workspace_root / ".electorn" / "checkpoints"
        self.checkpoints_dir.mkdir(parents=True, exist_ok=True)
        self.ignore_patterns = ignore_patterns or [
            ".git",
            "__pycache__",
            "node_modules",
            ".venv",
            "venv",
            ".electorn",
        ]

    def _get_tracked_files(self) -> list[Path]:
        """Collect all files eligible for snapshotting."""
        tracked = []
        for root, dirs, files in os.walk(self.workspace_root):
            dirs[:] = [d for d in dirs if not any(p in d for p in self.ignore_patterns)]
            for f in files:
                if any(p in f for p in self.ignore_patterns):
                    continue
                tracked.append(Path(root) / f)
        return tracked

    def create_checkpoint(self, message: str = "Automated checkpoint") -> str:
        """Create a full safe snapshot of the current workspace."""
        cid = f"cp-{int(time.time())}-{uuid.uuid4().hex[:4]}"
        target_dir = self.checkpoints_dir / cid
        target_dir.mkdir(parents=True, exist_ok=True)

        files = self._get_tracked_files()
        copied_rel = []

        for f in files:
            try:
                rel = f.relative_to(self.workspace_root)
                dest = target_dir / "data" / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, dest)
                copied_rel.append(rel.as_posix())
            except Exception:
                continue

        meta = CheckpointMeta(
            id=cid,
            timestamp=time.time(),
            iso_time=time.strftime("%Y-%m-%d %H:%M:%S"),
            message=message,
            files=copied_rel,
        )

        meta_file = target_dir / "meta.json"
        meta_file.write_text(json.dumps(meta.model_dump(), indent=2), encoding="utf-8")

        return cid

    def list_checkpoints(self) -> list[CheckpointMeta]:
        """List all available checkpoints ordered by newest first."""
        checkpoints: list[CheckpointMeta] = []
        if not self.checkpoints_dir.exists():
            return checkpoints

        for child in self.checkpoints_dir.iterdir():
            if child.is_dir() and (child / "meta.json").exists():
                try:
                    data = json.loads((child / "meta.json").read_text(encoding="utf-8"))
                    checkpoints.append(CheckpointMeta(**data))
                except Exception:
                    continue

        checkpoints.sort(key=lambda c: c.timestamp, reverse=True)
        return checkpoints

    def get_latest_checkpoint(self) -> Optional[CheckpointMeta]:
        """Retrieve the most recent checkpoint."""
        cps = self.list_checkpoints()
        return cps[0] if cps else None

    def diff(self, checkpoint_id: Optional[str] = None) -> str:
        """Compute unified diff between current workspace and the specified checkpoint."""
        cps = self.list_checkpoints()
        if not cps:
            return "No previous checkpoints recorded."

        target_cp = None
        if checkpoint_id:
            for c in cps:
                if c.id == checkpoint_id:
                    target_cp = c
                    break
        else:
            target_cp = cps[0]

        if not target_cp:
            return f"Checkpoint '{checkpoint_id}' not found."

        data_dir = self.checkpoints_dir / target_cp.id / "data"
        if not data_dir.exists():
            return f"Checkpoint data for '{target_cp.id}' is missing."

        diffs: list[str] = []
        current_files = {p.relative_to(self.workspace_root).as_posix(): p for p in self._get_tracked_files()}
        old_files = set(target_cp.files)

        all_keys = sorted(set(current_files.keys()).union(old_files))

        for k in all_keys:
            old_path = data_dir / k
            curr_path = current_files.get(k)

            old_text = old_path.read_text(encoding="utf-8", errors="replace") if old_path.exists() else ""
            curr_text = curr_path.read_text(encoding="utf-8", errors="replace") if curr_path and curr_path.exists() else ""

            if old_text != curr_text:
                patch = list(
                    difflib.unified_diff(
                        old_text.splitlines(keepends=True),
                        curr_text.splitlines(keepends=True),
                        fromfile=f"checkpoint/{k}",
                        tofile=f"workspace/{k}",
                    )
                )
                if patch:
                    diffs.append("".join(patch))

        return "\n".join(diffs) if diffs else "No differences between workspace and checkpoint."

    def rollback(self, checkpoint_id: Optional[str] = None) -> bool:
        """Restore workspace to the state preserved in the checkpoint."""
        cps = self.list_checkpoints()
        if not cps:
            return False

        target_cp = None
        if checkpoint_id:
            for c in cps:
                if c.id == checkpoint_id:
                    target_cp = c
                    break
        else:
            target_cp = cps[0]

        if not target_cp:
            return False

        data_dir = self.checkpoints_dir / target_cp.id / "data"
        if not data_dir.exists():
            return False

        # Restore preserved files
        for rel_str in target_cp.files:
            source = data_dir / rel_str
            dest = self.workspace_root / rel_str
            if source.exists():
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, dest)

        return True
