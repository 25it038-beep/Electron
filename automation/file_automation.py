"""Safe Filesystem Automation for Electorn AI.

Handles file creation, directory management, search, organization,
safe overwrites, and recoverable deletion.
"""

from __future__ import annotations

import os
import pathlib
import shutil
from typing import Any, Optional


class FileAutomation:
    """Provides validated, safe filesystem operations."""

    def __init__(self, base_workspace: Optional[str | pathlib.Path] = None) -> None:
        self.base_workspace = pathlib.Path(base_workspace or os.getcwd()).resolve()

    def resolve_path(self, target: str | pathlib.Path) -> pathlib.Path:
        """Resolve a relative or absolute path, expanding user directory."""
        p = pathlib.Path(target).expanduser()
        if p.is_absolute():
            return p.resolve()
        return (self.base_workspace / p).resolve()

    def create_folder(self, folder_path: str | pathlib.Path) -> dict[str, Any]:
        """Create a new directory and any necessary parent directories."""
        try:
            p = self.resolve_path(folder_path)
            p.mkdir(parents=True, exist_ok=True)
            return {
                "success": True,
                "path": str(p),
                "message": f"Created folder '{p.name}' at {p}.",
            }
        except Exception as err:
            return {"success": False, "message": f"Error creating folder: {err}"}

    def create_file(
        self,
        file_path: str | pathlib.Path,
        content: str = "",
        allow_overwrite: bool = False,
    ) -> dict[str, Any]:
        """Create a new text file with overwrite safeguards."""
        p = self.resolve_path(file_path)
        if p.exists() and not allow_overwrite:
            return {
                "success": False,
                "path": str(p),
                "requires_confirmation": True,
                "message": f"File '{p.name}' already exists. Overwrite requires confirmation.",
            }

        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            return {
                "success": True,
                "path": str(p),
                "bytes_written": len(content.encode("utf-8")),
                "message": f"Successfully created file '{p.name}' ({len(content)} chars).",
            }
        except Exception as err:
            return {"success": False, "message": f"Error writing file: {err}"}

    def read_file(self, file_path: str | pathlib.Path, max_chars: int = 50000) -> dict[str, Any]:
        """Read content of a supported text file."""
        p = self.resolve_path(file_path)
        if not p.exists() or not p.is_file():
            return {"success": False, "message": f"File '{p.name}' not found."}

        try:
            content = p.read_text(encoding="utf-8", errors="replace")
            truncated = len(content) > max_chars
            return {
                "success": True,
                "path": str(p),
                "content": content[:max_chars],
                "truncated": truncated,
                "message": f"Read {len(content)} characters from '{p.name}'.",
            }
        except Exception as err:
            return {"success": False, "message": f"Error reading file: {err}"}

    def move_file(self, src: str | pathlib.Path, dst: str | pathlib.Path) -> dict[str, Any]:
        """Move or rename a file safely."""
        src_p = self.resolve_path(src)
        dst_p = self.resolve_path(dst)

        if not src_p.exists():
            return {"success": False, "message": f"Source file '{src_p}' does not exist."}

        try:
            dst_p.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src_p), str(dst_p))
            return {
                "success": True,
                "src": str(src_p),
                "dst": str(dst_p),
                "message": f"Moved '{src_p.name}' to '{dst_p}'.",
            }
        except Exception as err:
            return {"success": False, "message": f"Move error: {err}"}

    def copy_file(self, src: str | pathlib.Path, dst: str | pathlib.Path) -> dict[str, Any]:
        """Copy a file to a new destination."""
        src_p = self.resolve_path(src)
        dst_p = self.resolve_path(dst)

        if not src_p.exists():
            return {"success": False, "message": f"Source file '{src_p}' not found."}

        try:
            dst_p.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(src_p), str(dst_p))
            return {
                "success": True,
                "src": str(src_p),
                "dst": str(dst_p),
                "message": f"Copied '{src_p.name}' to '{dst_p}'.",
            }
        except Exception as err:
            return {"success": False, "message": f"Copy error: {err}"}

    def find_files(self, directory: str | pathlib.Path, extension: Optional[str] = None, pattern: str = "*") -> list[str]:
        """Search directory for matching files."""
        dir_p = self.resolve_path(directory)
        if not dir_p.exists() or not dir_p.is_dir():
            return []

        glob_pattern = f"*.{extension.lstrip('.')}" if extension else pattern
        matches = []
        for path in dir_p.rglob(glob_pattern):
            if path.is_file():
                matches.append(str(path))
        return matches

    def organize_files_by_extension(self, source_dir: str | pathlib.Path, target_dir: str | pathlib.Path, ext: str) -> dict[str, Any]:
        """Move all files with a given extension (e.g. .pdf) into a specific folder."""
        src = self.resolve_path(source_dir)
        dst = self.resolve_path(target_dir)
        dst.mkdir(parents=True, exist_ok=True)

        moved_count = 0
        norm_ext = f".{ext.lstrip('.').lower()}"
        for item in src.iterdir():
            if item.is_file() and item.suffix.lower() == norm_ext:
                try:
                    shutil.move(str(item), str(dst / item.name))
                    moved_count += 1
                except Exception:
                    continue

        return {
            "success": True,
            "moved_count": moved_count,
            "target_dir": str(dst),
            "message": f"Organized {moved_count} {ext.upper()} files into '{dst.name}'.",
        }

    def open_path_in_explorer(self, target_path: str | pathlib.Path) -> dict[str, Any]:
        """Open a file or directory in Windows File Explorer."""
        p = self.resolve_path(target_path)
        try:
            if os.name == "nt":
                os.startfile(str(p))
            else:
                subprocess.Popen(["xdg-open", str(p)])
            return {"success": True, "path": str(p), "message": f"Opened '{p.name}' in File Explorer."}
        except Exception as err:
            return {"success": False, "message": f"Error opening path: {err}"}
