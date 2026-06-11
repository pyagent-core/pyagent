"""Tests for BlueprintDiffer: no changes, added, removed, modified."""

from __future__ import annotations

from pyagent_blueprint.differ import BlueprintDiffer, ChangeSeverity, ChangeType
from pyagent_blueprint.schema import (
    AgentSpec,
    BlueprintSpec,
    MetadataSpec,
    ProviderBindingSpec,
    WorkflowSpec,
)


def _base_spec() -> BlueprintSpec:
    return BlueprintSpec(
        metadata=MetadataSpec(name="test", version="1.0.0"),
        providers={"primary": ProviderBindingSpec(model="gpt-4o")},
        agents={"a": AgentSpec(prompt="Hello", provider="primary")},
        workflows={"w": WorkflowSpec(pattern="pipeline", agents={"a": "a"})},
    )


def test_no_changes() -> None:
    spec = _base_spec()
    differ = BlueprintDiffer()
    changes = differ.diff(spec, spec)
    assert len(changes) == 0


def test_added_agent() -> None:
    old = _base_spec()
    new_spec = _base_spec()
    new_data = new_spec.model_dump()
    new_data["agents"]["b"] = {"prompt": "New agent", "provider": "primary"}
    new = BlueprintSpec(**new_data)

    differ = BlueprintDiffer()
    changes = differ.diff(old, new)
    added = [c for c in changes if c.change_type == ChangeType.ADDED and "agents.b" in c.path]
    assert len(added) >= 1


def test_removed_agent() -> None:
    old = _base_spec()
    old_data = old.model_dump()
    old_data["agents"]["b"] = {"prompt": "Extra agent"}
    old = BlueprintSpec(**old_data)
    new = _base_spec()

    differ = BlueprintDiffer()
    changes = differ.diff(old, new)
    removed = [c for c in changes if c.change_type == ChangeType.REMOVED and "agents.b" in c.path]
    assert len(removed) >= 1


def test_modified_prompt_warning() -> None:
    old = _base_spec()
    new_data = old.model_dump()
    new_data["agents"]["a"]["prompt"] = "Changed prompt"
    new = BlueprintSpec(**new_data)

    differ = BlueprintDiffer()
    changes = differ.diff(old, new)
    prompt_changes = [
        c for c in changes if "prompt" in c.path and c.change_type == ChangeType.MODIFIED
    ]
    assert len(prompt_changes) >= 1
    assert prompt_changes[0].severity == ChangeSeverity.WARNING


def test_modified_pattern_breaking() -> None:
    old = _base_spec()
    new_data = old.model_dump()
    new_data["workflows"]["w"]["pattern"] = "fan_out_fan_in"
    new = BlueprintSpec(**new_data)

    differ = BlueprintDiffer()
    changes = differ.diff(old, new)
    pattern_changes = [c for c in changes if "pattern" in c.path]
    assert len(pattern_changes) >= 1
    assert pattern_changes[0].severity == ChangeSeverity.BREAKING


def test_summary_format() -> None:
    old = _base_spec()
    new_data = old.model_dump()
    new_data["agents"]["a"]["prompt"] = "Changed"
    new = BlueprintSpec(**new_data)

    differ = BlueprintDiffer()
    changes = differ.diff(old, new)
    summary = differ.summary(changes)
    assert "WARNING" in summary or "BREAKING" in summary or "INFO" in summary
