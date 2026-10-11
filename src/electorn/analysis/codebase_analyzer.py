"""Autonomous codebase context and multi-file analysis engine."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field


class SecurityFinding(BaseModel):
    """Potential security exposure found during repository inspection."""

    file_path: str
    line_number: int
    rule: str
    snippet_preview: str


class CodebaseSummary(BaseModel):
    """Structured inspection summary of an existing codebase."""

    root_dir: str
    total_files: int = 0
    total_lines: int = 0
    languages: dict[str, int] = Field(default_factory=dict)
    entry_points: list[str] = Field(default_factory=list)
    configuration_files: list[str] = Field(default_factory=list)
    route_endpoints: list[str] = Field(default_factory=list)
    database_models: list[str] = Field(default_factory=list)
    test_files: list[str] = Field(default_factory=list)
    security_findings: list[SecurityFinding] = Field(default_factory=list)
    primary_tech_stack: list[str] = Field(default_factory=list)


class CodebaseAnalyzer:
    """Analyzes repository structure, entry points, dependencies, and security hygiene."""

    SECRET_PATTERNS = [
        (r"(?i)(?:api_key|apikey|secret_key|private_key|token)\s*=\s*['\"][A-Za-z0-9_\-\.]{16,}['\"]", "Hardcoded API Key/Token"),
        (r"(?i)ghp_[A-Za-z0-9]{36}", "GitHub Personal Access Token"),
        (r"(?i)sk-[A-Za-z0-9]{32,}", "OpenAI API Key"),
        (r"(?i)(?:password|passwd|pwd)\s*=\s*['\"][^'\"]{6,}['\"]", "Hardcoded Password"),
    ]

    def __init__(self, workspace_root: Path | str, ignore_patterns: Optional[list[str]] = None):
        self.workspace_root = Path(workspace_root).resolve()
        self.ignore_patterns = ignore_patterns or [
            ".git",
            "__pycache__",
            "node_modules",
            ".venv",
            "venv",
            ".electorn",
            "dist",
            "build",
            ".pytest_cache",
        ]

    def analyze(self) -> CodebaseSummary:
        """Run complete codebase discovery and produce structured summary."""
        summary = CodebaseSummary(root_dir=str(self.workspace_root))

        for root, dirs, files in os.walk(self.workspace_root):
            dirs[:] = [d for d in dirs if not any(p in d for p in self.ignore_patterns)]

            for f in files:
                if any(p in f for p in self.ignore_patterns):
                    continue

                full_path = Path(root) / f
                rel_path = full_path.relative_to(self.workspace_root).as_posix()
                summary.total_files += 1

                ext = full_path.suffix.lower()
                lang = self._detect_language(ext)
                if lang:
                    summary.languages[lang] = summary.languages.get(lang, 0) + 1

                # Detect configuration & entry points
                lower_f = f.lower()
                if lower_f in ("main.py", "app.py", "index.ts", "index.js", "server.js", "main.go", "cli.py"):
                    summary.entry_points.append(rel_path)

                if lower_f in ("pyproject.toml", "package.json", "requirements.txt", "dockerfile", "docker-compose.yml", ".env.example", ".electorn.yaml"):
                    summary.configuration_files.append(rel_path)

                if lower_f.startswith("test_") or lower_f.endswith("_test.py") or "/tests/" in rel_path or "/test/" in rel_path:
                    summary.test_files.append(rel_path)

                # Inspect file contents safely
                if full_path.is_file() and full_path.stat().st_size < 1_000_000:
                    try:
                        text = full_path.read_text(encoding="utf-8", errors="replace")
                        summary.total_lines += len(text.splitlines())
                        self._scan_file_content(rel_path, text, summary)
                    except Exception:
                        pass

        summary.primary_tech_stack = self._infer_tech_stack(summary)
        return summary

    def _detect_language(self, ext: str) -> Optional[str]:
        mapping = {
            ".py": "Python",
            ".ts": "TypeScript",
            ".js": "JavaScript",
            ".tsx": "React (TSX)",
            ".jsx": "React (JSX)",
            ".html": "HTML",
            ".css": "CSS",
            ".go": "Go",
            ".rs": "Rust",
            ".sql": "SQL",
            ".json": "JSON",
            ".yaml": "YAML",
            ".yml": "YAML",
            ".md": "Markdown",
        }
        return mapping.get(ext)

    def _scan_file_content(self, rel_path: str, text: str, summary: CodebaseSummary) -> None:
        """Scan file text for routes, models, and potential hardcoded secrets."""
        # 1. Routes detection
        route_matches = re.findall(r"@(?:app|router)\.(?:get|post|put|delete|patch)\(\s*['\"]([^'\"]+)['\"]", text)
        for r in route_matches:
            summary.route_endpoints.append(f"{rel_path}: {r}")

        # 2. Database models detection
        model_matches = re.findall(r"class\s+([A-Za-z0-9_]+)\s*\((?:Base|SQLModel|Model|db\.Model)\)", text)
        for m in model_matches:
            summary.database_models.append(f"{rel_path}: {m}")

        # 3. Secret scanner
        for idx, line in enumerate(text.splitlines(), start=1):
            for pattern, rule in self.SECRET_PATTERNS:
                if re.search(pattern, line):
                    summary.security_findings.append(
                        SecurityFinding(
                            file_path=rel_path,
                            line_number=idx,
                            rule=rule,
                            snippet_preview=line.strip()[:60] + "...",
                        )
                    )

    def _infer_tech_stack(self, summary: CodebaseSummary) -> list[str]:
        stack = []
        if "Python" in summary.languages:
            stack.append("Python")
        if "TypeScript" in summary.languages or "JavaScript" in summary.languages:
            stack.append("Node.js/JavaScript")
        if "React (TSX)" in summary.languages or "React (JSX)" in summary.languages:
            stack.append("React")
        if any("requirements.txt" in c or "pyproject.toml" in c for c in summary.configuration_files):
            if any("fastapi" in r.lower() for r in summary.route_endpoints) or summary.route_endpoints:
                stack.append("FastAPI / REST API")
        if summary.database_models:
            stack.append("SQL / ORM Persistence")
        if any("dockerfile" in c.lower() for c in summary.configuration_files):
            stack.append("Docker")
        return stack
