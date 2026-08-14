---
description: "The PyAgent Blueprint Specification (pyagent/v1) — versioning policy, compilation/validation/diff/contract-testing semantics, and the extension namespace. The authoritative JSON Schema is published at /blueprint-schema.json."
---

# The PyAgent Blueprint Specification

This page is the formal reference for what a `pyagent-blueprint` YAML document *means* — not a
tutorial (see the [Blueprint guide](../guides/blueprint.md) for that), but the semantics each
operation (`validate`, `compile`, `diff`, `test`) actually guarantees.

## Versioning

Every blueprint declares `api_version: pyagent/v1`. Schema versions are tracked in
`pyagent_blueprint.extensions.SCHEMA_VERSIONS` with an explicit frozen/unfrozen flag:

- **`pyagent/v1` is frozen.** Once shipped, no breaking changes to it — only non-breaking
  documentation or bugfix corrections. Any structural addition or removal requires a new version.
  A `pyagent/v1` blueprint written today keeps working indefinitely.
- Unknown `api_version` values are treated as **not frozen** (i.e. still in development) by
  `pyagent_blueprint.extensions.is_frozen()`.

## The authoritative schema

[**pyagent.org/blueprint-schema.json**](../blueprint-schema.json) is generated directly from the
real `pydantic.BaseModel` (`BlueprintSpec`) that `pyagent-blueprint` validates every YAML document
against — via `scripts/gen_docs.py`, checked in CI (`gen_docs.py --check`) so it can never drift
from the actual validator. It is not a hand-maintained approximation.

## Compilation semantics

"Compiling" a blueprint means passing its `BlueprintIR` (parsed from `BlueprintSpec`) to a
`RuntimeAdapter.compile()` — there is no runtime-independent compiled form; compilation is always
*onto* a specific adapter (`pyagent`, `langgraph`, `crewai`, ...). Two guarantees hold across every
adapter, enforced by the shared `AdapterConformanceSuite`:

1. **Governance is never silently dropped.** A declared budget, SLA, memory tier, guardrail,
   recovery policy, or human-in-the-loop checkpoint is either honored by the target adapter, or the
   compile step surfaces a stable diagnostic code (`DiagnosticSeverity.WARNING` or `.ERROR`) —
   `BUDGET_UNSUPPORTED`, `SLA_UNSUPPORTED`, `MEMORY_TIER_UNSUPPORTED`, and others in
   `pyagent_blueprint.diagnostics`, one per identified gap (`G1`–`G10`). `DiagnosticSeverity.INFO`
   codes (e.g. `PATTERN_LOWERED`) are expected, not failures — they note a lossless
   representation change, not a dropped feature.
2. **Pattern intent is preserved.** A `supervisor` pattern compiles to *something* that actually
   routes between the declared agents on the target runtime — not an approximation the conformance
   suite can't tell apart from a different pattern.

## Validation semantics

`pyagent-blueprint validate` runs static checks *before* any adapter sees the spec: schema
conformance (via the pydantic model), dangling references (an agent referenced by a workflow that
doesn't exist in `agents:`), and, when a `RuntimeAdapter` is installed, pattern-name validity
against that adapter's declared vocabulary — best-effort and adapter-dependent, since not every
adapter has a fixed pattern vocabulary (e.g. a bare loop-based adapter). No LLM call happens during
validation.

## Diff semantics

`pyagent-blueprint diff old.yaml new.yaml` produces a list of `Change` records — `path` (dotted
field path), `change_type` (`ADDED` / `REMOVED` / `MODIFIED`), and `severity`:

- `INFO` — a change with no behavioral impact.
- `WARNING` — a change worth a reviewer's attention but not breaking.
- `BREAKING` — a change that alters the system's observable behavior (e.g. removing an agent a
  workflow still references, changing a workflow's pattern).

This is a semantic diff over the IR, not a text diff of YAML — reordering keys produces no changes;
changing a provider binding does.

## Contract-testing semantics

`pyagent-blueprint test` runs `BlueprintTester` — contract-conformance checks executed against a
deterministic `MockLLM`, never a live model call. It validates the system's *shape* (every declared
workflow runs end-to-end, contracts' input/output constraints are satisfiable) without spending a
token or requiring API credentials, which is what makes it safe to run in CI on every commit.

## Extension and customization rules

Constructs a blueprint needs that have no native field in `BlueprintSpec` go under the reserved
`x-pyagent` key prefix (`pyagent_blueprint.extensions.EXTENSION_NAMESPACE`), mirroring the pattern
used by JSON Schema's own vendor-extension convention. Any key under this namespace is:

- **Additive** — never required for a document to validate.
- **Round-trip-safe by construction** — a consumer that doesn't recognize an `x-pyagent:*` key must
  ignore it gracefully, not fail.

`contract.py`'s SLA metadata (which has no native JSON Schema equivalent) is the current real
example: it's surfaced under `x-pyagent` in the published per-workflow contract schema rather than
forcing SLA into core JSON Schema vocabulary.

## See also

- [Blueprint pillar overview](blueprint.md) — what it solves, when to use it
- [Blueprint guide](../guides/blueprint.md) — tutorial and full YAML field reference
- [Why Blueprint?](../why-blueprint.md) — the case against hand-written orchestration code
- [pyagent.org/blueprint-schema.json](../blueprint-schema.json) — the authoritative schema
