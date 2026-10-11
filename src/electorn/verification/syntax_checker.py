"""Fast multi-language static syntax checker."""

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Optional
from pydantic import BaseModel
import yaml
from electorn.workspace.file_manager import FileManager


class SyntaxCheckResult(BaseModel):
    """Result of static syntax validation for a file."""

    file_path: str
    is_valid: bool
    error_message: Optional[str] = None
    line_number: Optional[int] = None
    column_number: Optional[int] = None


class SyntaxChecker:
    """Performs static syntax verification on generated source files."""

    def __init__(self, file_manager: FileManager):
        self.file_manager = file_manager

    def check_file(self, relative_path: str) -> SyntaxCheckResult:
        """Validate syntax of a single file based on extension."""
        path = Path(relative_path)
        ext = path.suffix.lower()

        try:
            content = self.file_manager.read_file(relative_path)
        except Exception as err:
            return SyntaxCheckResult(
                file_path=relative_path,
                is_valid=False,
                error_message=f"Could not read file: {err}",
            )

        if ext == ".py":
            return self._check_python(relative_path, content)
        elif ext == ".json":
            return self._check_json(relative_path, content)
        elif ext in (".yaml", ".yml"):
            return self._check_yaml(relative_path, content)

        # For JS/TS/HTML/CSS without dedicated native compilers installed, pass basic sanity
        return SyntaxCheckResult(file_path=relative_path, is_valid=True)

    def _check_python(self, file_path: str, content: str) -> SyntaxCheckResult:
        """Parse Python AST to detect syntax errors before execution."""
        try:
            ast.parse(content, filename=file_path)
            return SyntaxCheckResult(file_path=file_path, is_valid=True)
        except SyntaxError as exc:
            return SyntaxCheckResult(
                file_path=file_path,
                is_valid=False,
                error_message=f"{exc.msg} at line {exc.lineno}",
                line_number=exc.lineno,
                column_number=exc.offset,
            )

    def _check_json(self, file_path: str, content: str) -> SyntaxCheckResult:
        """Validate JSON format."""
        try:
            json.loads(content)
            return SyntaxCheckResult(file_path=file_path, is_valid=True)
        except json.JSONDecodeError as exc:
            return SyntaxCheckResult(
                file_path=file_path,
                is_valid=False,
                error_message=exc.msg,
                line_number=exc.lineno,
                column_number=exc.colno,
            )

    def _check_yaml(self, file_path: str, content: str) -> SyntaxCheckResult:
        """Validate YAML format."""
        try:
            yaml.safe_load(content)
            return SyntaxCheckResult(file_path=file_path, is_valid=True)
        except Exception as exc:
            return SyntaxCheckResult(
                file_path=file_path,
                is_valid=False,
                error_message=str(exc),
            )

    def check_all_files(self, file_list: list[str]) -> list[SyntaxCheckResult]:
        """Validate all files in a manifest or change list."""
        return [self.check_file(f) for f in file_list]
