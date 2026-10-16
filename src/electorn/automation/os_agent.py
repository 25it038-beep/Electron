"""Full Windows OS Automation Agent for Electorn AI.

Provides safe application launching, window management, directory organization,
system resource diagnostics, and guarded PowerShell command execution.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

try:
    import pywinauto
    from pywinauto import Desktop
    PYWINAUTO_AVAILABLE = True
except ImportError:
    PYWINAUTO_AVAILABLE = False

logger = logging.getLogger(__name__)


class WindowsOSAgent:
    """Intelligent OS automation agent managing desktop applications, windows, files, and system resources."""

    # Common Windows application aliases mapped to executable commands
    KNOWN_APPLICATIONS = {
        "notepad": "notepad.exe",
        "calculator": "calc.exe",
        "calc": "calc.exe",
        "explorer": "explorer.exe",
        "file explorer": "explorer.exe",
        "terminal": "wt.exe",
        "windows terminal": "wt.exe",
        "powershell": "powershell.exe",
        "cmd": "cmd.exe",
        "command prompt": "cmd.exe",
        "code": "code",
        "vs code": "code",
        "vscode": "code",
        "edge": "msedge.exe",
        "microsoft edge": "msedge.exe",
        "chrome": "chrome.exe",
        "google chrome": "chrome.exe",
        "paint": "mspaint.exe",
        "task manager": "taskmgr.exe",
        "taskmgr": "taskmgr.exe",
        "wordpad": "write.exe",
    }

    # Destructive or catastrophic shell patterns prohibited from autonomous execution
    DANGEROUS_PATTERNS = [
        r"\bformat\s+[a-z]:",
        r"\brmdir\s+[\/a-z0-9\s]*[a-z]:\\",
        r"\bdel\s+[\/a-z0-9\s]*[a-z]:\\(?:windows|system32)",
        r"\bdiskpart\b",
        r"\bbcdedit\b",
        r"\btakeown\s+\/f\s+[a-z]:\\windows",
        r":\(\)\{\s*:\|:&\s*\};:",
        r"\bRemove-Item\s+.*[a-z]:\\",
    ]

    # File categorization rules for directory cleaning
    FILE_CATEGORIES = {
        "Documents": {".pdf", ".docx", ".doc", ".txt", ".pptx", ".ppt", ".xlsx", ".xls", ".csv", ".epub", ".rtf", ".odt"},
        "Code": {".py", ".js", ".jsx", ".ts", ".tsx", ".html", ".css", ".json", ".yaml", ".yml", ".sql", ".sh", ".ps1", ".rs", ".go", ".c", ".cpp", ".h"},
        "Images": {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp", ".ico", ".tiff"},
        "Media": {".mp3", ".wav", ".flac", ".mp4", ".mkv", ".mov", ".avi", ".webm", ".m4a"},
        "Archives": {".zip", ".tar", ".gz", ".7z", ".rar", ".bz2", ".xz"},
        "Installers": {".exe", ".msi", ".iso", ".bat", ".cmd"},
    }

    def __init__(self, audit_log_path: Optional[Path] = None) -> None:
        self.audit_log_path = audit_log_path or (Path.home() / ".electorn" / "os_audit.jsonl")
        self.audit_log_path.parent.mkdir(parents=True, exist_ok=True)

    def _log_action(self, action: str, details: Dict[str, Any], success: bool = True) -> None:
        """Record executed OS action to the local security audit log."""
        record = {
            "timestamp": time.time(),
            "time_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "action": action,
            "success": success,
            "details": details,
        }
        try:
            with open(self.audit_log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")
        except Exception as e:
            logger.debug("Failed writing OS audit log: %s", e)

    # =========================================================================
    # 1. APPLICATION LAUNCHING & PROCESS MANAGEMENT
    # =========================================================================

    def launch_application(self, app_name_or_path: str, arguments: str = "") -> Dict[str, Any]:
        """Launch a desktop application by name or executable path."""
        key = app_name_or_path.strip().lower()
        cmd = self.KNOWN_APPLICATIONS.get(key, app_name_or_path.strip())

        try:
            full_cmd = f"{cmd} {arguments}".strip() if arguments else cmd
            proc = subprocess.Popen(
                full_cmd,
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
            )
            res = {
                "success": True,
                "message": f"Successfully launched '{app_name_or_path}' (PID: {proc.pid}).",
                "pid": proc.pid,
                "command": full_cmd,
            }
            self._log_action("launch_application", res, success=True)
            return res
        except Exception as err:
            res = {
                "success": False,
                "message": f"Failed to launch '{app_name_or_path}': {err}",
                "error": str(err),
            }
            self._log_action("launch_application", res, success=False)
            return res

    def close_application(self, process_name_or_pid: Any) -> Dict[str, Any]:
        """Terminate a running application by process name or PID."""
        if not PSUTIL_AVAILABLE:
            return {"success": False, "message": "Process management requires psutil library."}

        closed_count = 0
        try:
            if isinstance(process_name_or_pid, int) or str(process_name_or_pid).isdigit():
                pid = int(process_name_or_pid)
                p = psutil.Process(pid)
                p.terminate()
                closed_count = 1
            else:
                target_name = str(process_name_or_pid).lower()
                if not target_name.endswith(".exe"):
                    target_name_exe = f"{target_name}.exe"
                else:
                    target_name_exe = target_name

                for proc in psutil.process_iter(["pid", "name"]):
                    try:
                        pname = (proc.info.get("name") or "").lower()
                        if pname in (target_name, target_name_exe):
                            proc.terminate()
                            closed_count += 1
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue

            if closed_count > 0:
                res = {"success": True, "message": f"Terminated {closed_count} instance(s) of '{process_name_or_pid}'."}
            else:
                res = {"success": False, "message": f"No active process found matching '{process_name_or_pid}'."}
            self._log_action("close_application", res, success=res["success"])
            return res
        except Exception as err:
            res = {"success": False, "message": f"Error closing process: {err}"}
            self._log_action("close_application", res, success=False)
            return res

    def list_running_applications(self, limit: int = 15) -> List[Dict[str, Any]]:
        """List active user-level GUI applications and top resource consumers."""
        if not PSUTIL_AVAILABLE:
            return []

        procs: List[Dict[str, Any]] = []
        for p in psutil.process_iter(["pid", "name", "memory_percent", "cpu_percent"]):
            try:
                info = p.info
                name = info.get("name") or ""
                # Filter background system noise
                if name.lower() in ("system idle process", "system", "registry", "smss.exe", "csrss.exe"):
                    continue
                procs.append({
                    "pid": info.get("pid"),
                    "name": name,
                    "memory_percent": round(info.get("memory_percent") or 0.0, 1),
                    "cpu_percent": round(info.get("cpu_percent") or 0.0, 1),
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        # Sort by memory usage
        procs.sort(key=lambda x: x["memory_percent"], reverse=True)
        return procs[:limit]

    # =========================================================================
    # 2. WINDOW MANAGEMENT
    # =========================================================================

    def get_open_windows(self) -> List[str]:
        """Retrieve list of currently open visible top-level windows."""
        if not PYWINAUTO_AVAILABLE or sys.platform != "win32":
            return []

        results: List[str] = []
        try:
            for w in Desktop(backend="uia").windows():
                try:
                    title = w.window_text()
                    if title and len(title.strip()) > 1:
                        results.append(title.strip())
                except Exception:
                    continue
        except Exception as e:
            logger.debug("Error listing windows via pywinauto: %s", e)

        return results

    def focus_window(self, title_query: str) -> Dict[str, Any]:
        """Bring a window containing title_query into the foreground."""
        if not PYWINAUTO_AVAILABLE or sys.platform != "win32":
            return {"success": False, "message": "Window control requires pywinauto on Windows."}

        try:
            query = title_query.lower()
            for w in Desktop(backend="uia").windows():
                try:
                    title = (w.window_text() or "").lower()
                    if query in title:
                        w.set_focus()
                        res = {"success": True, "message": f"Focused window: '{w.window_text()}'."}
                        self._log_action("focus_window", res, success=True)
                        return res
                except Exception:
                    continue

            return {"success": False, "message": f"Could not find window matching '{title_query}'."}
        except Exception as e:
            return {"success": False, "message": f"Error focusing window: {e}"}

    # =========================================================================
    # 3. DIRECTORY CLEANING & FILE ORGANIZER
    # =========================================================================

    def organize_directory(
        self,
        target_dir: Optional[Any] = None,
        target_dir_path: Optional[Any] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Organize files in a messy directory (e.g. Downloads or Desktop) into categorized subfolders."""
        raw_target = target_dir if target_dir is not None else (target_dir_path if target_dir_path is not None else (Path.home() / "Downloads"))
        target = Path(raw_target).expanduser().resolve()
        if not target.exists() or not target.is_dir():
            return {"success": False, "message": f"Target directory does not exist: {target}"}

        moves: List[Dict[str, str]] = []
        skipped = 0

        # Scan files directly in the root of target directory
        for item in list(target.iterdir()):
            if item.is_dir() or item.name.startswith("."):
                continue

            ext = item.suffix.lower()
            assigned_category = "Other"
            for cat_name, extensions in self.FILE_CATEGORIES.items():
                if ext in extensions:
                    assigned_category = cat_name
                    break

            if assigned_category == "Other":
                skipped += 1
                continue

            destination_dir = target / assigned_category
            destination_file = destination_dir / item.name

            # Resolve name conflicts
            if destination_file.exists():
                stem = item.stem
                counter = 1
                while destination_file.exists():
                    destination_file = destination_dir / f"{stem}_{counter}{ext}"
                    counter += 1

            moves.append({
                "source": str(item),
                "destination": str(destination_file),
                "category": assigned_category,
                "file_name": item.name,
            })

            if not dry_run:
                destination_dir.mkdir(parents=True, exist_ok=True)
                shutil.move(str(item), str(destination_file))

        summary = {
            "success": True,
            "target_directory": str(target),
            "files_moved": len(moves),
            "skipped_unrecognized": skipped,
            "dry_run": dry_run,
            "moved_items": moves[:50],  # Return first 50 items
            "message": f"Organized {len(moves)} file(s) into category folders in '{target.name}'." if not dry_run else f"Preview: {len(moves)} file(s) would be organized.",
        }
        self._log_action("organize_directory", {"target": str(target), "count": len(moves), "dry_run": dry_run}, success=True)
        return summary

    # =========================================================================
    # 4. SYSTEM DIAGNOSTICS & STORAGE INSPECTION
    # =========================================================================

    def get_system_diagnostics(self) -> Dict[str, Any]:
        """Inspect storage space across drives, CPU, RAM, and battery state."""
        if not PSUTIL_AVAILABLE:
            return {"error": "psutil library required for system diagnostics."}

        # 1. Disk usage
        drives = []
        for part in psutil.disk_partitions(all=False):
            try:
                usage = psutil.disk_usage(part.mountpoint)
                drives.append({
                    "device": part.device,
                    "mountpoint": part.mountpoint,
                    "fstype": part.fstype,
                    "total_gb": round(usage.total / (1024 ** 3), 1),
                    "used_gb": round(usage.used / (1024 ** 3), 1),
                    "free_gb": round(usage.free / (1024 ** 3), 1),
                    "percent_used": usage.percent,
                })
            except (PermissionError, OSError):
                continue

        # 2. Virtual Memory
        mem = psutil.virtual_memory()
        mem_info = {
            "total_gb": round(mem.total / (1024 ** 3), 1),
            "available_gb": round(mem.available / (1024 ** 3), 1),
            "percent_used": mem.percent,
        }

        # 3. CPU
        cpu_percent = psutil.cpu_percent(interval=0.1)
        cpu_count = psutil.cpu_count(logical=True)

        # 4. Battery
        battery = psutil.sensors_battery()
        bat_info = None
        if battery:
            bat_info = {
                "percent": battery.percent,
                "power_plugged": battery.power_plugged,
            }

        import platform
        return {
            "drives": drives,
            "memory": mem_info,
            "cpu": {
                "percent_used": cpu_percent,
                "core_count": cpu_count,
            },
            "battery": bat_info,
            "os": {
                "system": platform.system(),
                "release": platform.release(),
                "version": platform.version(),
                "machine": platform.machine(),
            },
        }

    # =========================================================================
    # 5. GUARDED POWERSHELL & SHELL EXECUTION
    # =========================================================================

    def execute_powershell_guarded(
        self,
        command: str,
        timeout_seconds: int = 45,
    ) -> Dict[str, Any]:
        """Execute guarded PowerShell command and surface explicit guardrail reason."""
        res = self.execute_command_safely(command, timeout_seconds=timeout_seconds)
        if res.get("blocked"):
            res["reason"] = f"Security guardrail violation: {res.get('message', 'Destructive operation blocked.')}"
        return res

    def execute_command_safely(
        self,
        command: str,
        cwd: Optional[Path] = None,
        timeout_seconds: int = 45,
    ) -> Dict[str, Any]:
        """Execute a terminal/PowerShell command with strict security guardrails against destructive instructions."""
        clean_cmd = command.strip()

        # Check safety guardrails
        for pat in self.DANGEROUS_PATTERNS:
            if re.search(pat, clean_cmd, re.IGNORECASE):
                res = {
                    "success": False,
                    "blocked": True,
                    "exit_code": -1,
                    "message": f"Execution blocked: Command matches prohibited safety pattern '{pat}'. Destructive operations require explicit manual execution.",
                    "command": clean_cmd,
                }
                self._log_action("execute_command_safely", res, success=False)
                return res

        start_time = time.time()
        try:
            # On Windows: execute via powershell.exe -NoProfile -NonInteractive
            if sys.platform == "win32":
                args = ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", clean_cmd]
            else:
                args = ["/bin/bash", "-c", clean_cmd]

            proc = subprocess.run(
                args,
                cwd=str(cwd) if cwd else None,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
            )
            duration_ms = int((time.time() - start_time) * 1000)

            res = {
                "success": proc.returncode == 0,
                "blocked": False,
                "exit_code": proc.returncode,
                "stdout": proc.stdout.strip(),
                "stderr": proc.stderr.strip(),
                "duration_ms": duration_ms,
                "command": clean_cmd,
            }
            self._log_action("execute_command_safely", {
                "command": clean_cmd,
                "exit_code": proc.returncode,
                "duration_ms": duration_ms,
            }, success=proc.returncode == 0)
            return res

        except subprocess.TimeoutExpired:
            res = {
                "success": False,
                "blocked": False,
                "exit_code": -1,
                "stdout": "",
                "stderr": f"Command timed out after {timeout_seconds} seconds.",
                "duration_ms": int((time.time() - start_time) * 1000),
                "command": clean_cmd,
            }
            self._log_action("execute_command_safely", res, success=False)
            return res
        except Exception as err:
            res = {
                "success": False,
                "blocked": False,
                "exit_code": -1,
                "stdout": "",
                "stderr": str(err),
                "duration_ms": int((time.time() - start_time) * 1000),
                "command": clean_cmd,
            }
            self._log_action("execute_command_safely", res, success=False)
            return res
