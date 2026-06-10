"""GovernanceService: validation, compliance scoring, diff generation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pyagent_blueprint import (
    BlueprintDiffer,
    BlueprintValidator,
    load_blueprint,
)
from pyagent_blueprint.differ import Change
from pyagent_blueprint.schema import BlueprintSpec
from pyagent_blueprint.validator import IssueSeverity, ValidationIssue


@dataclass
class ComplianceReport:
    """Governance compliance report.

    Attributes:
        total_checks: Number of checks performed.
        passed: Number passing.
        issues: List of validation issues.
        score: Compliance score (0.0–1.0).
    """

    total_checks: int
    passed: int
    issues: list[ValidationIssue]
    score: float


class GovernanceService:
    """Run governance checks on blueprints.

    Combines validation, compliance scoring, and diffing.
    """

    def __init__(self) -> None:
        self._validator = BlueprintValidator()
        self._differ = BlueprintDiffer()

    def check_compliance(self, spec: BlueprintSpec) -> ComplianceReport:
        """Run all validation checks and compute compliance score.

        Args:
            spec: Blueprint to check.

        Returns:
            ``ComplianceReport`` with score and issues.
        """
        issues = self._validator.validate(spec)
        # Count checks as: 6 standard categories
        total_checks = 6
        error_count = sum(1 for i in issues if i.severity == IssueSeverity.ERROR)
        passed = max(0, total_checks - error_count)
        score = passed / total_checks if total_checks > 0 else 1.0

        return ComplianceReport(
            total_checks=total_checks,
            passed=passed,
            issues=issues,
            score=score,
        )

    def diff(self, old: BlueprintSpec, new: BlueprintSpec) -> list[Change]:
        """Compute semantic diff between two specs.

        Args:
            old: Previous version.
            new: Updated version.

        Returns:
            List of ``Change`` objects.
        """
        return self._differ.diff(old, new)

    def diff_summary(self, old: BlueprintSpec, new: BlueprintSpec) -> str:
        """Human-readable diff summary.

        Args:
            old: Previous version.
            new: Updated version.

        Returns:
            Summary string.
        """
        changes = self.diff(old, new)
        return self._differ.summary(changes)

    def format_report(self, report: ComplianceReport) -> str:
        """Format a compliance report as text."""
        lines: list[str] = []
        lines.append(f"Compliance Score: {report.score:.0%} ({report.passed}/{report.total_checks})")

        if report.issues:
            lines.append("\nIssues:")
            for issue in report.issues:
                lines.append(f"  [{issue.severity}] {issue.path}: {issue.message}")
        else:
            lines.append("No issues found.")

        return "\n".join(lines)
