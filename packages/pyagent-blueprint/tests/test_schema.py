"""Tests for BlueprintSpec: valid round-trip, invalid specs, defaults."""

from __future__ import annotations

import pytest
from pyagent_blueprint.schema import (
    AgentSpec,
    BlueprintSpec,
    ContractSpec,
    MetadataSpec,
    ProviderBindingSpec,
    RecoverySpec,
    WorkflowSpec,
)
from pydantic import ValidationError


def test_valid_spec_roundtrip() -> None:
    spec = BlueprintSpec(
        metadata=MetadataSpec(name="test", version="1.0.0"),
        providers={"primary": ProviderBindingSpec(model="gpt-4o")},
        agents={"greeter": AgentSpec(prompt="Say hello", provider="primary")},
        workflows={
            "main": WorkflowSpec(pattern="pipeline", agents={"stages": {"greeter": "greeter"}})
        },
    )
    dumped = spec.model_dump()
    restored = BlueprintSpec(**dumped)
    assert restored.metadata.name == "test"
    assert restored.agents["greeter"].prompt == "Say hello"


def test_missing_metadata_fails() -> None:
    with pytest.raises(ValidationError):
        BlueprintSpec(
            agents={"a": AgentSpec(prompt="x")},
            workflows={"w": WorkflowSpec(pattern="p")},
        )


def test_missing_agents_fails() -> None:
    with pytest.raises(ValidationError):
        BlueprintSpec(
            metadata=MetadataSpec(name="test"),
            workflows={"w": WorkflowSpec(pattern="p")},
        )


def test_workflow_misplaced_wiring_key_rejected() -> None:
    """A pattern-wiring key (e.g. `classifier:`/`routes:`) placed as a
    sibling of `pattern:` instead of nested under `agents:` must raise a
    clear ValidationError, not silently produce an empty `agents={}` that
    only fails later at run time (see PyAgentAdapter.run -> AttributeError:
    'NoneType' object has no attribute 'run')."""
    with pytest.raises(ValidationError, match="classifier"):
        WorkflowSpec(pattern="supervisor", classifier="scorer", routes={"hot": "account_exec"})


def test_workflow_agents_config_recovery_guardrails_still_allowed() -> None:
    WorkflowSpec(
        pattern="pipeline",
        agents={"stages": ["a", "b"]},
        config={"rounds": 2},
        recovery=RecoverySpec(max_retries=1),
        guardrails=["pii"],
    )


def test_optional_fields_default() -> None:
    spec = BlueprintSpec(
        metadata=MetadataSpec(name="minimal"),
        agents={"a": AgentSpec(prompt="x")},
        workflows={"w": WorkflowSpec(pattern="pipeline")},
    )
    assert spec.providers == {}
    assert spec.context is None
    assert spec.contracts == {}
    assert spec.observability is None
    assert spec.api_version == "pyagent/v1"


def test_contract_sla_defaults() -> None:
    contract = ContractSpec()
    assert contract.sla.latency_p95_ms == 5000.0
    assert contract.sla.cost_max_usd == 0.10
