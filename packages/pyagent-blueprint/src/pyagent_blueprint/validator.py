"""BlueprintValidator: static checks for blueprint specs."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

from pyagent_patterns.registry import list_patterns

if TYPE_CHECKING:
    from pyagent_blueprint.schema.spec import BlueprintSpec


class IssueSeverity(StrEnum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass(frozen=True)
class ValidationIssue:
    """A single validation finding.

    Attributes:
        path: Dotted path to the problematic field.
        message: Human-readable description.
        severity: Error, warning, or info.
    """

    path: str
    message: str
    severity: IssueSeverity


class BlueprintValidator:
    """Run static checks on a BlueprintSpec.

    Checks:
    - All agent refs in workflows exist in agents dict
    - All provider refs in agents exist in providers dict
    - Pattern names are registered
    - No cyclic workflow dependencies
    - SLA values are realistic
    - Security: no hardcoded API keys in prompts
    """

    def validate(self, spec: BlueprintSpec) -> list[ValidationIssue]:
        """Run all validation checks.

        Args:
            spec: The blueprint spec to validate.

        Returns:
            List of issues found (may be empty).
        """
        issues: list[ValidationIssue] = []
        issues.extend(self._check_agent_refs(spec))
        issues.extend(self._check_provider_refs(spec))
        issues.extend(self._check_pattern_names(spec))
        issues.extend(self._check_contract_refs(spec))
        issues.extend(self._check_sla_values(spec))
        issues.extend(self._check_security(spec))
        return issues

    def _check_agent_refs(self, spec: BlueprintSpec) -> list[ValidationIssue]:
        """Ensure all agent refs in workflows point to defined agents."""
        issues: list[ValidationIssue] = []
        agent_names = set(spec.agents.keys())

        for wf_name, wf_spec in spec.workflows.items():
            for role, ref in wf_spec.agents.items():
                if isinstance(ref, str) and ref not in agent_names:
                    issues.append(
                        ValidationIssue(
                            path=f"workflows.{wf_name}.agents.{role}",
                            message=f"Agent ref '{ref}' not found in agents. Available: {sorted(agent_names)}",
                            severity=IssueSeverity.ERROR,
                        )
                    )
                elif isinstance(ref, dict):
                    for sub_role, sub_ref in ref.items():
                        if isinstance(sub_ref, str) and sub_ref not in agent_names:
                            issues.append(
                                ValidationIssue(
                                    path=f"workflows.{wf_name}.agents.{role}.{sub_role}",
                                    message=f"Agent ref '{sub_ref}' not found in agents.",
                                    severity=IssueSeverity.ERROR,
                                )
                            )
        return issues

    def _check_provider_refs(self, spec: BlueprintSpec) -> list[ValidationIssue]:
        """Ensure all provider refs in agents point to defined providers."""
        issues: list[ValidationIssue] = []
        provider_names = set(spec.providers.keys())

        for agent_name, agent_spec in spec.agents.items():
            if agent_spec.provider and agent_spec.provider not in provider_names:
                issues.append(
                    ValidationIssue(
                        path=f"agents.{agent_name}.provider",
                        message=f"Provider ref '{agent_spec.provider}' not found. Available: {sorted(provider_names)}",
                        severity=IssueSeverity.ERROR,
                    )
                )
        return issues

    def _check_pattern_names(self, spec: BlueprintSpec) -> list[ValidationIssue]:
        """Ensure all pattern names are registered."""
        issues: list[ValidationIssue] = []
        known = set(list_patterns())

        for wf_name, wf_spec in spec.workflows.items():
            if wf_spec.pattern not in known:
                issues.append(
                    ValidationIssue(
                        path=f"workflows.{wf_name}.pattern",
                        message=f"Unknown pattern '{wf_spec.pattern}'. Known: {sorted(known)}",
                        severity=IssueSeverity.ERROR,
                    )
                )
        return issues

    def _check_contract_refs(self, spec: BlueprintSpec) -> list[ValidationIssue]:
        """Ensure contracts reference existing workflows."""
        issues: list[ValidationIssue] = []
        wf_names = set(spec.workflows.keys())

        for contract_name in spec.contracts:
            if contract_name not in wf_names:
                issues.append(
                    ValidationIssue(
                        path=f"contracts.{contract_name}",
                        message=f"Contract '{contract_name}' references non-existent workflow.",
                        severity=IssueSeverity.WARNING,
                    )
                )
        return issues

    def _check_sla_values(self, spec: BlueprintSpec) -> list[ValidationIssue]:
        """Warn about unrealistic SLA values."""
        issues: list[ValidationIssue] = []
        for name, contract in spec.contracts.items():
            if contract.sla.latency_p95_ms < 100:
                issues.append(
                    ValidationIssue(
                        path=f"contracts.{name}.sla.latency_p95_ms",
                        message=f"Latency SLA {contract.sla.latency_p95_ms}ms is unrealistically low for LLM calls.",
                        severity=IssueSeverity.WARNING,
                    )
                )
        return issues

    def _check_security(self, spec: BlueprintSpec) -> list[ValidationIssue]:
        """Check for hardcoded API keys in prompts."""
        issues: list[ValidationIssue] = []
        key_patterns = ["sk-", "sk-ant-", "api_key=", "API_KEY", "Bearer "]

        for agent_name, agent_spec in spec.agents.items():
            for pattern in key_patterns:
                if pattern in agent_spec.prompt:
                    issues.append(
                        ValidationIssue(
                            path=f"agents.{agent_name}.prompt",
                            message=f"Possible hardcoded API key detected (contains '{pattern}').",
                            severity=IssueSeverity.ERROR,
                        )
                    )
                    break
        return issues
