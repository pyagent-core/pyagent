"""Tests for BlueprintValidator: dangling refs, unknown patterns, security."""

from __future__ import annotations

from pyagent_blueprint.schema import (
    AgentSpec,
    BlueprintSpec,
    ContractSpec,
    MetadataSpec,
    ProviderBindingSpec,
    WorkflowSpec,
)
from pyagent_blueprint.validator import BlueprintValidator, IssueSeverity


def _make_spec(**overrides) -> BlueprintSpec:
    defaults = {
        "metadata": MetadataSpec(name="test"),
        "providers": {"primary": ProviderBindingSpec(model="gpt-4o")},
        "agents": {"a": AgentSpec(prompt="test", provider="primary")},
        "workflows": {"w": WorkflowSpec(pattern="pipeline", agents={"stages": {"a": "a"}})},
    }
    defaults.update(overrides)
    return BlueprintSpec(**defaults)


def test_valid_spec_no_issues() -> None:
    spec = _make_spec()
    validator = BlueprintValidator()
    issues = validator.validate(spec)
    assert len(issues) == 0


def test_dangling_agent_ref() -> None:
    spec = _make_spec(
        workflows={"w": WorkflowSpec(pattern="pipeline", agents={"x": "nonexistent"})},
    )
    validator = BlueprintValidator()
    issues = validator.validate(spec)
    errors = [i for i in issues if i.severity == IssueSeverity.ERROR and "Agent ref" in i.message]
    assert len(errors) >= 1


def test_dangling_provider_ref() -> None:
    spec = _make_spec(
        agents={"a": AgentSpec(prompt="test", provider="nonexistent")},
    )
    validator = BlueprintValidator()
    issues = validator.validate(spec)
    errors = [i for i in issues if i.severity == IssueSeverity.ERROR and "Provider ref" in i.message]
    assert len(errors) >= 1


def test_unknown_pattern() -> None:
    spec = _make_spec(
        workflows={"w": WorkflowSpec(pattern="unknown_xyz", agents={"a": "a"})},
    )
    validator = BlueprintValidator()
    issues = validator.validate(spec)
    errors = [i for i in issues if "Unknown pattern" in i.message]
    assert len(errors) >= 1


def test_security_check_api_key() -> None:
    spec = _make_spec(
        agents={"a": AgentSpec(prompt="Use sk-abc123 to authenticate", provider="primary")},
    )
    validator = BlueprintValidator()
    issues = validator.validate(spec)
    errors = [i for i in issues if "API key" in i.message]
    assert len(errors) >= 1


def test_contract_dangling_workflow() -> None:
    spec = _make_spec(
        contracts={"nonexistent_workflow": ContractSpec()},
    )
    validator = BlueprintValidator()
    issues = validator.validate(spec)
    warnings = [i for i in issues if i.severity == IssueSeverity.WARNING and "non-existent workflow" in i.message]
    assert len(warnings) >= 1
