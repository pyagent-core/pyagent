"""contract.py: published JSON Schema for BlueprintIR I/O contracts.

Per mega-plan Section 1.2 (`contract.py (NEW) JSON Schema I/O contracts`)
and G10 ("Python-only SDK" — mitigated by publishing a JSON Schema for the
IR so non-Python tooling can validate/consume blueprints without this
package).

Deliberately dependency-free (no `jsonschema` import required to *use*
this module — only to *validate against* it, which callers opt into).
`ContractIR.input_schema`/`output_schema` are already JSON-Schema-shaped
dicts (see `ir.py`); this module adds:

- `contract_json_schema(contract)` — wraps a `ContractIR` into a single
  JSON Schema document describing the workflow's input/output contract
  plus its SLA as `x-pyagent` metadata (SLA has no native JSON Schema
  equivalent — see `diagnostics.SLA_UNSUPPORTED`).
- `BLUEPRINT_IR_META_SCHEMA` — a hand-authored JSON Schema describing the
  shape of `BlueprintIR` itself (agents/workflows/contracts/memory), for
  non-Python consumers that want to validate a serialized IR document.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pyagent_blueprint.ir import BlueprintIR, ContractIR

CONTRACT_SCHEMA_VERSION = "pyagent-contract/v1"


def contract_json_schema(contract: ContractIR) -> dict[str, Any]:
    """Render a single workflow's `ContractIR` as a JSON Schema document.

    The document's `$id`-less shape is intentionally minimal: `input`/
    `output` are the declared JSON Schemas verbatim (empty dict means
    "unconstrained"), and SLA constraints are surfaced under the
    `x-pyagent` extension namespace since they have no native JSON
    Schema representation — a non-Python consumer can still read them,
    it's just not part of core JSON Schema vocabulary.
    """
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": f"pyagent-blueprint contract: {contract.workflow}",
        "type": "object",
        "properties": {
            "input": contract.input_schema or {"description": "unconstrained"},
            "output": contract.output_schema or {"description": "unconstrained"},
        },
        "x-pyagent": {
            "schema_version": CONTRACT_SCHEMA_VERSION,
            "sla": {
                "latency_p95_ms": contract.sla.latency_p95_ms,
                "cost_max_usd": contract.sla.cost_max_usd,
                "quality_min": contract.sla.quality_min,
            },
        },
    }


def blueprint_contracts_json_schema(ir: BlueprintIR) -> dict[str, dict[str, Any]]:
    """Render every declared contract in a `BlueprintIR` as JSON Schema
    documents, keyed by workflow name."""
    return {name: contract_json_schema(contract) for name, contract in ir.contracts.items()}


# Hand-authored meta-schema describing BlueprintIR's own shape, for
# non-Python tooling that wants to validate a serialized IR document
# (e.g. the output of a future `pyagent-blueprint compile --emit-ir`).
# Deliberately permissive (`additionalProperties: true`) since the IR is
# still evolving — this documents the stable core, not a closed contract.
BLUEPRINT_IR_META_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://pyagent.org/schema/blueprint-ir/v1.json",
    "title": "pyagent-blueprint IR",
    "type": "object",
    "required": ["api_version", "name", "version", "agents", "workflows"],
    "properties": {
        "api_version": {"type": "string"},
        "name": {"type": "string"},
        "version": {"type": "string"},
        "agents": {
            "type": "object",
            "additionalProperties": {
                "type": "object",
                "required": ["name", "prompt"],
                "properties": {
                    "name": {"type": "string"},
                    "prompt": {"type": "string"},
                    "provider": {"type": "string"},
                    "tools": {"type": "array", "items": {"type": "string"}},
                    "guardrails": {"type": "array", "items": {"type": "string"}},
                },
            },
        },
        "workflows": {
            "type": "object",
            "additionalProperties": {
                "type": "object",
                "required": ["name", "pattern"],
                "properties": {
                    "name": {"type": "string"},
                    "pattern": {"type": "string"},
                    "agents": {"type": "object"},
                    "config": {"type": "object"},
                },
            },
        },
        "contracts": {"type": "object"},
        "memory": {"type": ["object", "null"]},
    },
    "additionalProperties": True,
}
