"""Tests for pyagent_blueprint.contract (mega-plan Section 1.2 contract.py)."""

from __future__ import annotations

from pyagent_blueprint.contract import (
    BLUEPRINT_IR_META_SCHEMA,
    blueprint_contracts_json_schema,
    contract_json_schema,
)
from pyagent_blueprint.ir import SLAIR, ContractIR


def test_contract_json_schema_shape() -> None:
    contract = ContractIR(
        workflow="main",
        input_schema={"type": "string"},
        output_schema={"type": "string"},
        sla=SLAIR(latency_p95_ms=1000.0, cost_max_usd=0.05, quality_min=0.9),
    )
    schema = contract_json_schema(contract)

    assert schema["properties"]["input"] == {"type": "string"}
    assert schema["properties"]["output"] == {"type": "string"}
    assert schema["x-pyagent"]["sla"]["latency_p95_ms"] == 1000.0
    assert schema["x-pyagent"]["sla"]["cost_max_usd"] == 0.05


def test_contract_json_schema_unconstrained_default() -> None:
    contract = ContractIR(workflow="main")
    schema = contract_json_schema(contract)
    assert schema["properties"]["input"] == {"description": "unconstrained"}


def test_blueprint_contracts_json_schema_keyed_by_workflow() -> None:
    from pyagent_blueprint.conformance import CANONICAL_FIXTURES

    ir = CANONICAL_FIXTURES["governance"]
    schemas = blueprint_contracts_json_schema(ir)
    assert "main" in schemas
    assert schemas["main"]["x-pyagent"]["schema_version"] == "pyagent-contract/v1"


def test_meta_schema_has_required_top_level_keys() -> None:
    assert BLUEPRINT_IR_META_SCHEMA["required"] == [
        "api_version",
        "name",
        "version",
        "agents",
        "workflows",
    ]
    assert "agents" in BLUEPRINT_IR_META_SCHEMA["properties"]
    assert "workflows" in BLUEPRINT_IR_META_SCHEMA["properties"]
