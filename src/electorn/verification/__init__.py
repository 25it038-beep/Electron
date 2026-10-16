"""Verification, automated syntax analysis, test execution, and self-repair engine."""

from electorn.verification.syntax_checker import SyntaxChecker, SyntaxCheckResult
from electorn.verification.test_runner import TestRunner, TestRunResult
from electorn.verification.self_repair import SelfRepairEngine, RepairAttempt
from electorn.verification.improvement_agent import SystemSelfImprovementAgent, DiagnosisReport, ProposedPatch

__all__ = [
    "SyntaxChecker",
    "SyntaxCheckResult",
    "TestRunner",
    "TestRunResult",
    "SelfRepairEngine",
    "RepairAttempt",
    "SystemSelfImprovementAgent",
    "DiagnosisReport",
    "ProposedPatch",
]
