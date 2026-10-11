"""Autonomous, sandboxed file manager with diffs and path verification."""

from __future__ import annotations

import difflib
import os
import shutil
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field
from electorn.workspace.permissions import PermissionManager


class FileOperationResult(BaseModel):
    """Result of an autonomous file modification."""

    path: str
    action: str  # "created", "modified", "deleted", "skipped", "error"
    diff: Optional[str] = None
    bytes_written: int = 0
    message: Optional[str] = None
    success: bool = True


class FileManager:
    """Manages reading, writing, and organizing files strictly within a workspace."""

    def __init__(
        self,
        workspace_root: Path | str,
        permissions: Optional[PermissionManager] = None,
        ignore_patterns: Optional[list[str]] = None,
    ):
        self.workspace_root = Path(workspace_root).resolve()
        self.workspace_root.mkdir(parents=True, exist_ok=True)
        self.permissions = permissions or PermissionManager(auto_approve=True)
        self.ignore_patterns = ignore_patterns or [
            ".git",
            "__pycache__",
            "node_modules",
            ".venv",
            "venv",
            ".electorn",
        ]

    def resolve_safe_path(self, relative_or_absolute: str | Path) -> Path:
        """Resolve path ensuring it does not escape the workspace directory."""
        raw_path = Path(relative_or_absolute)
        if raw_path.is_absolute():
            resolved = raw_path.resolve()
        else:
            resolved = (self.workspace_root / raw_path).resolve()

        # Security check: must reside inside workspace_root
        try:
            resolved.relative_to(self.workspace_root)
        except ValueError as err:
            raise PermissionError(
                f"Path traversal detected! Path '{relative_or_absolute}' escapes workspace '{self.workspace_root}'"
            ) from err

        return resolved

    def read_file(self, path: str | Path) -> str:
        """Read text content of a workspace file."""
        target = self.resolve_safe_path(path)
        if not target.is_file():
            raise FileNotFoundError(f"File not found: {path}")
        return target.read_text(encoding="utf-8")

    def write_file(self, path: str | Path, content: str, backup: bool = True) -> FileOperationResult:
        """Write content to file inside workspace, creating parent directories if needed."""
        target = self.resolve_safe_path(path)
        rel_str = str(target.relative_to(self.workspace_root))

        target.parent.mkdir(parents=True, exist_ok=True)

        is_existing = target.exists()
        old_content = ""
        diff_str: Optional[str] = None

        if is_existing:
            if not self.permissions.request_file_write(target, is_overwrite=True):
                return FileOperationResult(
                    path=rel_str,
                    action="skipped",
                    message="Permission denied by user",
                    success=False,
                )
            try:
                old_content = target.read_text(encoding="utf-8")
            except Exception:
                old_content = ""

            if backup:
                self._create_backup(target)

            diff_lines = list(
                difflib.unified_diff(
                    old_content.splitlines(keepends=True),
                    content.splitlines(keepends=True),
                    fromfile=f"a/{rel_str}",
                    tofile=f"b/{rel_str}",
                )
            )
            diff_str = "".join(diff_lines) if diff_lines else None
        else:
            if not self.permissions.request_file_write(target, is_overwrite=False):
                return FileOperationResult(
                    path=rel_str,
                    action="skipped",
                    message="Permission denied by user",
                    success=False,
                )

        target.write_text(content, encoding="utf-8")
        return FileOperationResult(
            path=rel_str,
            action="modified" if is_existing else "created",
            diff=diff_str,
            bytes_written=len(content.encode("utf-8")),
            success=True,
        )

    def delete_file(self, path: str | Path) -> FileOperationResult:
        """Safely delete a file inside the workspace."""
        target = self.resolve_safe_path(path)
        rel_str = str(target.relative_to(self.workspace_root))

        if not target.exists():
            return FileOperationResult(path=rel_str, action="skipped", message="File does not exist")

        if target.is_file():
            target.unlink()
        elif target.is_dir():
            shutil.rmtree(target)

        return FileOperationResult(path=rel_str, action="deleted", success=True)

    def list_files(self, max_depth: int = 5) -> list[str]:
        """List relative paths of all relevant files in the workspace."""
        results: list[str] = []
        for root, dirs, files in os.walk(self.workspace_root):
            # Prune ignored directories in-place
            dirs[:] = [
                d
                for d in dirs
                if not any(pattern in d for pattern in self.ignore_patterns)
            ]

            rel_root = Path(root).relative_to(self.workspace_root)
            depth = len(rel_root.parts)
            if depth > max_depth:
                continue

            for f in files:
                if any(pattern in f for pattern in self.ignore_patterns):
                    continue
                file_rel = (rel_root / f).as_posix() if str(rel_root) != "." else f
                results.append(file_rel)

        return sorted(results)

    def get_directory_tree_str(self) -> str:
        """Return formatted string tree representation of workspace files."""
        files = self.list_files()
        if not files:
            return "(Empty workspace)"
        return "\n".join(f"├── {f}" for f in files)

    def _create_backup(self, target: Path) -> None:
        """Create a backup of an existing file in .electorn/backups/."""
        backup_dir = self.workspace_root / ".electorn" / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        rel = target.relative_to(self.workspace_root)
        backup_file = backup_dir / f"{rel.name}.bak"
        try:
            shutil.copy2(target, backup_file)
        except Exception:
            pass
