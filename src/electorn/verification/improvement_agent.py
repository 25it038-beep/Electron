"""Controlled Self-Improvement & System Diagnosis Agent for Electorn AI.

Analyzes execution logs, detects recurring failures, performs dependency audits,
and proposes safe, sandboxed architectural patches with automated rollback options.
"""

from __future__ import annotations

import ast
import difflib
import json
import logging
from pathlib import Path
import re
import shutil
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class DiagnosisReport(BaseModel):
    """Result of a system health and log diagnostic audit."""
    timestamp: float = Field(default_factory=time.time)
    errors_found: List[Dict[str, Any]] = Field(default_factory=list)
    recent_errors: List[Dict[str, Any]] = Field(default_factory=list)
    missing_dependencies: List[str] = Field(default_factory=list)
    runtimes: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    health_score: int = 100
    recommendations: List[str] = Field(default_factory=list)
    summary: str = ""


class ProposedPatch(BaseModel):
    """A proposed, reviewable code patch with safety verification and rollback capability."""
    patch_id: str
    target_file: str
    diff: str
    is_verified_safe: bool = False
    safety_notes: List[str] = Field(default_factory=list)
    created_at: float = Field(default_factory=time.time)
    applied: bool = False


class SystemSelfImprovementAgent:
    """Audits Electorn execution health, analyzes log failures, and crafts safe reviewable patches."""

    REQUIRED_PACKAGES = [
        ("psutil", "System resource diagnostics and process management"),
        ("fastapi", "Video-call server and REST API infrastructure"),
        ("uvicorn", "Asynchronous HTTP & WebSocket server"),
        ("edge_tts", "High-fidelity modern neural speech synthesis"),
        ("speech_recognition", "Microphone listening and audio capture"),
        ("pywinauto", "Windows GUI desktop automation"),
        ("playwright", "Autonomous browser navigation and DOM research"),
    ]

    UNSAFE_PATTERNS = [
        r"__import__\s*\(\s*['\"]os['\"]\s*\)\.system",
        r"\bexec\s*\(",
        r"\beval\s*\(",
        r"format\s+[a-z]:",
        r"rmdir\s+[\/a-z]*\s+[a-z]:\\",
    ]

    def __init__(self, workspace: Optional[Path] = None) -> None:
        self.workspace = workspace or Path.cwd()
        self.log_dir = Path.home() / ".electorn"

    # =========================================================================
    # 1. SYSTEM CAPABILITY & RUNTIME DIAGNOSIS
    # =========================================================================

    def audit_system(self) -> DiagnosisReport:
        """Alias for diagnose_system."""
        return self.diagnose_system()

    def diagnose_system(self) -> DiagnosisReport:
        """Audit runtime health, verify installed automation libraries, and scan recent logs."""
        missing = []
        recommendations = []
        runtimes = {}

        # Audit packages
        for pkg, desc in self.REQUIRED_PACKAGES:
            try:
                __import__(pkg)
                runtimes[pkg] = {"installed": True, "details": desc}
            except ImportError:
                missing.append(pkg)
                recommendations.append(f"Install optional package '{pkg}' ({desc}).")
                runtimes[pkg] = {"installed": False, "details": desc}

        # Analyze logs
        error_logs = self.scan_recent_logs()
        score = 100 - (len(missing) * 8) - (min(len(error_logs), 10) * 3)
        score = max(20, min(100, score))

        if error_logs:
            recommendations.append(f"Found {len(error_logs)} recent exception trace(s) in audit logs. Review log details.")

        summary = f"Health Score: {score}/100. "
        if not missing and not error_logs:
            summary += "All core automation, voice, and research subsystems are healthy."
        else:
            summary += f"{len(missing)} missing package(s), {len(error_logs)} logged error(s)."

        return DiagnosisReport(
            errors_found=error_logs[:15],
            recent_errors=error_logs[:15],
            missing_dependencies=missing,
            runtimes=runtimes,
            health_score=score,
            recommendations=recommendations,
            summary=summary,
        )

    def scan_recent_logs(self) -> List[Dict[str, Any]]:
        """Extract recent exceptions from activity and audit log files."""
        errors: List[Dict[str, Any]] = []
        if not self.log_dir.exists():
            return errors

        log_files = list(self.log_dir.glob("*.jsonl")) + list((self.log_dir / "companion").glob("*.jsonl"))
        for log_file in log_files:
            try:
                with open(log_file, "r", encoding="utf-8", errors="replace") as f:
                    for line in f:
                        if not line.strip():
                            continue
                        try:
                            record = json.loads(line)
                            if not record.get("success", True) or "error" in record.get("details", {}):
                                errors.append({
                                    "file": log_file.name,
                                    "action": record.get("action", "unknown"),
                                    "details": record.get("details", {}),
                                    "timestamp": record.get("timestamp"),
                                })
                        except Exception:
                            continue
            except Exception:
                continue

        return errors

    # =========================================================================
    # 2. CONTROLLED PATCH GENERATION & SAFETY VERIFICATION
    # =========================================================================

    def propose_patch(
        self,
        patch_id: str,
        target_file: Path,
        proposed_code: str,
    ) -> ProposedPatch:
        """Create a reviewable unified diff and run static safety checks."""
        if not target_file.exists():
            raise FileNotFoundError(f"Target file {target_file} does not exist.")

        with open(target_file, "r", encoding="utf-8") as f:
            original_code = f.read()

        # Compute Unified Diff
        diff_lines = list(difflib.unified_diff(
            original_code.splitlines(keepends=True),
            proposed_code.splitlines(keepends=True),
            fromfile=f"a/{target_file.name}",
            tofile=f"b/{target_file.name}",
        ))
        diff_text = "".join(diff_lines)

        safety_notes: List[str] = []
        is_safe = True

        # Safety Check 1: Valid Python Syntax
        if target_file.suffix == ".py":
            try:
                ast.parse(proposed_code)
                safety_notes.append("✔ Valid Python syntax.")
            except SyntaxError as e:
                is_safe = False
                safety_notes.append(f"✖ Syntax error in proposed patch: {e}")

        # Safety Check 2: Check for Unsafe Patterns
        for pat in self.UNSAFE_PATTERNS:
            if re.search(pat, proposed_code, re.IGNORECASE):
                is_safe = False
                safety_notes.append(f"✖ Prohibited unsafe pattern detected: '{pat}'.")

        # Safety Check 3: Check that file wasn't completely emptied
        if len(proposed_code.strip()) < len(original_code.strip()) * 0.2:
            is_safe = False
            safety_notes.append("✖ Patch drastically reduces file size (>80% deletion). Blocked.")

        if is_safe:
            safety_notes.append("✔ Passes all automated security guardrails.")

        return ProposedPatch(
            patch_id=patch_id,
            target_file=str(target_file),
            diff=diff_text,
            is_verified_safe=is_safe,
            safety_notes=safety_notes,
        )

    def apply_patch(self, patch: ProposedPatch, new_code: str) -> Dict[str, Any]:
        """Apply a verified patch after creating an automatic .bak backup file."""
        if not patch.is_verified_safe:
            return {"success": False, "message": "Cannot apply patch: Failed safety verification."}

        target = Path(patch.target_file)
        if not target.exists():
            return {"success": False, "message": f"Target file '{target}' missing."}

        backup_file = target.with_suffix(f"{target.suffix}.bak")
        try:
            # Create backup
            shutil.copy2(target, backup_file)

            # Write proposed code
            with open(target, "w", encoding="utf-8") as f:
                f.write(new_code)

            patch.applied = True
            return {
                "success": True,
                "message": f"Successfully applied patch '{patch.patch_id}'. Backup saved to '{backup_file.name}'.",
                "backup_path": str(backup_file),
            }
        except Exception as e:
            # Rollback immediately on error
            if backup_file.exists():
                shutil.copy2(backup_file, target)
            return {"success": False, "message": f"Error applying patch, rolled back: {e}"}

    def rollback_patch(self, target_file_path: str) -> Dict[str, Any]:
        """Rollback a file to its .bak backup state."""
        target = Path(target_file_path)
        backup_file = target.with_suffix(f"{target.suffix}.bak")

        if not backup_file.exists():
            return {"success": False, "message": f"No backup file found at '{backup_file}'."}

        try:
            shutil.copy2(backup_file, target)
            backup_file.unlink()
            return {"success": True, "message": f"Successfully rolled back '{target.name}' to backup."}
        except Exception as e:
            return {"success": False, "message": f"Failed to rollback: {e}"}
