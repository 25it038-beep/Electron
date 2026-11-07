"""Storage, Disk Management, and File Organization Controller for Windows.

Provides drive capacity analytics, large file scans, duplicate detection,
temp space optimization, and intelligent downloads/desktop organization.
"""
from __future__ import annotations

import hashlib
import logging
import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class StorageController:
    """Manages drive telemetry, disk space optimization, and file organization."""

    def get_drive_overview(self) -> Dict[str, Any]:
        """Get capacity, used space, free space, and usage percent for all mounted drives."""
        import psutil

        drives: List[Dict[str, Any]] = []
        for part in psutil.disk_partitions(all=False):
            # Exclude CD-ROM or unmounted drives
            if "cdrom" in part.opts or part.fstype == "":
                continue
            try:
                usage = psutil.disk_usage(part.mountpoint)
                drives.append({
                    "device": part.device,
                    "mountpoint": part.mountpoint,
                    "fstype": part.fstype,
                    "total_gb": round(usage.total / (1024**3), 2),
                    "used_gb": round(usage.used / (1024**3), 2),
                    "free_gb": round(usage.free / (1024**3), 2),
                    "percent_used": usage.percent,
                    "is_critical": usage.percent > 95.0,
                })
            except Exception as e:
                logger.debug(f"Could not read drive {part.mountpoint}: {e}")

        return {
            "success": True,
            "drives": drives,
            "total_drives": len(drives),
        }

    def find_large_files(self, target_dir: Optional[str] = None, min_size_mb: int = 100, limit: int = 20) -> Dict[str, Any]:
        """Scan a directory for files larger than min_size_mb, ordered by size descending."""
        if not target_dir:
            target_dir = str(Path.home())

        min_bytes = min_size_mb * 1024 * 1024
        large_files: List[Dict[str, Any]] = []

        try:
            for root, dirs, files in os.walk(target_dir):
                # Skip hidden/system directories for performance
                dirs[:] = [d for d in dirs if not d.startswith(".") and d.lower() not in ("node_modules", "appdata", "$recycle.bin")]
                for f in files:
                    full_p = os.path.join(root, f)
                    try:
                        st = os.stat(full_p)
                        if st.st_size >= min_bytes:
                            large_files.append({
                                "path": full_p,
                                "name": f,
                                "size_mb": round(st.st_size / (1024 * 1024), 2),
                                "size_gb": round(st.st_size / (1024**3), 2),
                            })
                    except (PermissionError, FileNotFoundError, OSError):
                        continue
        except Exception as e:
            logger.debug(f"Large file scan error: {e}")

        # Sort descending by size
        large_files.sort(key=lambda x: x["size_mb"], reverse=True)
        return {
            "success": True,
            "target_dir": target_dir,
            "min_size_mb": min_size_mb,
            "count": len(large_files[:limit]),
            "files": large_files[:limit],
        }

    def analyze_temp_files(self) -> Dict[str, Any]:
        """Calculate total size of temporary files in user and system temp folders."""
        temp_paths = [os.environ.get("TEMP"), os.environ.get("TMP"), "C:\\Windows\\Temp"]
        total_bytes = 0
        file_count = 0

        for tp in filter(None, temp_paths):
            if not os.path.exists(tp):
                continue
            for root, _, files in os.walk(tp):
                for f in files:
                    full_p = os.path.join(root, f)
                    try:
                        total_bytes += os.path.getsize(full_p)
                        file_count += 1
                    except (PermissionError, FileNotFoundError, OSError):
                        continue

        return {
            "success": True,
            "temp_files_count": file_count,
            "total_size_mb": round(total_bytes / (1024 * 1024), 2),
            "total_size_gb": round(total_bytes / (1024**3), 2),
        }

    def clean_temp_files(self, dry_run: bool = True) -> Dict[str, Any]:
        """Safely remove unlocked temporary files. If dry_run is True, only estimates savings."""
        if dry_run:
            analysis = self.analyze_temp_files()
            analysis["mode"] = "dry_run"
            analysis["message"] = f"Dry run: estimated {analysis['total_size_mb']} MB can be cleaned."
            return analysis

        user_temp = os.environ.get("TEMP")
        cleaned_bytes = 0
        cleaned_files = 0
        skipped_files = 0

        if user_temp and os.path.exists(user_temp):
            for root, dirs, files in os.walk(user_temp, topdown=False):
                for f in files:
                    fp = os.path.join(root, f)
                    try:
                        sz = os.path.getsize(fp)
                        os.remove(fp)
                        cleaned_bytes += sz
                        cleaned_files += 1
                    except Exception:
                        skipped_files += 1
                for d in dirs:
                    dp = os.path.join(root, d)
                    try:
                        os.rmdir(dp)
                    except Exception:
                        pass

        return {
            "success": True,
            "cleaned_files": cleaned_files,
            "cleaned_mb": round(cleaned_bytes / (1024 * 1024), 2),
            "skipped_locked_files": skipped_files,
        }

    def organize_directory(self, target_dir: Optional[str] = None) -> Dict[str, Any]:
        """Organize files in target directory (e.g. Downloads or Desktop) into categorized subfolders."""
        if not target_dir:
            target_dir = str(Path.home() / "Downloads")

        target_path = Path(target_dir)
        if not target_path.exists():
            return {"success": False, "error": f"Directory not found: {target_dir}"}

        categories = {
            "Documents": [".pdf", ".docx", ".doc", ".txt", ".xlsx", ".pptx", ".csv", ".epub"],
            "Images": [".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".svg", ".ico"],
            "Videos": [".mp4", ".mkv", ".mov", ".avi", ".webm", ".wmv"],
            "Audio": [".mp3", ".wav", ".aac", ".flac", ".ogg", ".m4a"],
            "Archives": [".zip", ".rar", ".7z", ".tar", ".gz", ".iso"],
            "Installers": [".exe", ".msi", ".bat", ".cmd"],
            "Code": [".py", ".ts", ".js", ".html", ".css", ".json", ".rs", ".cpp", ".java"],
        }

        moved_counts: Dict[str, int] = {k: 0 for k in categories}

        for item in target_path.iterdir():
            if item.is_file():
                ext = item.suffix.lower()
                dest_category = None
                for cat, extensions in categories.items():
                    if ext in extensions:
                        dest_category = cat
                        break
                if dest_category:
                    cat_dir = target_path / dest_category
                    cat_dir.mkdir(exist_ok=True)
                    try:
                        dest_file = cat_dir / item.name
                        if not dest_file.exists():
                            shutil.move(str(item), str(dest_file))
                            moved_counts[dest_category] += 1
                    except Exception as e:
                        logger.debug(f"Failed to move {item.name}: {e}")

        total_moved = sum(moved_counts.values())
        return {
            "success": True,
            "target_dir": target_dir,
            "total_files_organized": total_moved,
            "breakdown": moved_counts,
        }
