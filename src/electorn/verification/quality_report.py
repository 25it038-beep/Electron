"""Quality verification report generation and test auditing."""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field
from rich.table import Table


class ExecutedCheck(BaseModel):
    """Record of an executed verification check."""

    name: str
    command_or_action: str
    exit_code: int
    output_snippet: str
    passed: bool


class QualityReport(BaseModel):
    """Comprehensive quality verification report."""

    project_name: str
    executed_checks: list[ExecutedCheck] = Field(default_factory=list)
    tests_passed: int = 0
    tests_failed: int = 0
    syntax_errors: list[str] = Field(default_factory=list)
    security_warnings: list[str] = Field(default_factory=list)
    skipped_checks: list[str] = Field(default_factory=list)
    outstanding_issues: list[str] = Field(default_factory=list)

    @property
    def final_status(self) -> str:
        """Derive explicit honest status."""
        if not self.executed_checks and not self.syntax_errors:
            return "NOT VERIFIED"

        has_failures = (
            any(not c.passed for c in self.executed_checks)
            or self.tests_failed > 0
            or len(self.syntax_errors) > 0
        )
        if has_failures:
            return "FAILED"

        if self.security_warnings or self.skipped_checks:
            return "PASS WITH WARNINGS"

        return "PASS"

    def format_terminal_table(self) -> Table:
        """Format the report into a Rich Table."""
        status = self.final_status
        status_color = "green" if status == "PASS" else ("yellow" if status == "PASS WITH WARNINGS" else "red")

        table = Table(
            title=f"🛡️ Quality Verification Report: {self.project_name} [bold {status_color}]({status})[/bold {status_color}]",
            border_style="cyan",
        )
        table.add_column("Check / Verification", style="bold white")
        table.add_column("Command / Action", style="dim")
        table.add_column("Result", style="bold")
        table.add_column("Details", style="dim")

        for c in self.executed_checks:
            res_str = "[green]✔ PASS[/green]" if c.passed else f"[red]✖ FAIL (code {c.exit_code})[/red]"
            table.add_row(c.name, c.command_or_action, res_str, c.output_snippet[:60])

        if self.syntax_errors:
            table.add_row("Syntax Checks", "AST / Compiler", "[red]✖ ERRORS[/red]", f"{len(self.syntax_errors)} files with errors")
        else:
            table.add_row("Syntax Checks", "AST / Compiler", "[green]✔ PASS[/green]", "All files syntactically valid")

        if self.security_warnings:
            table.add_row("Security Scan", "Secret hygiene", "[yellow]⚠ WARNING[/yellow]", f"{len(self.security_warnings)} warnings")
        else:
            table.add_row("Security Scan", "Secret hygiene", "[green]✔ PASS[/green]", "No hardcoded credentials found")

        for s in self.skipped_checks:
            table.add_row("Skipped Check", s, "[dim]SKIPPED[/dim]", "Prerequisites not present")

        return table
