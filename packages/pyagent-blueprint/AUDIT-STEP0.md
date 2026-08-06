# Step 0 — Repo Audit (Track A, Mega Plan Part 1 §1.4)

Verified directly against `packages/pyagent-blueprint` source on this branch. All `[RE-VERIFY IN STEP 0]` / `[VERIFY IN REPO]` markers from the mega plan are resolved below.

## Package layout (actual)

```
src/pyagent_blueprint/
├── __init__.py       re-exports BlueprintCompiler, BlueprintDiffer, BlueprintGenerator,
│                      BlueprintLoadError, load_blueprint, load_blueprint_from_str,
│                      BlueprintRenderer, RuntimeGraph, schema types, BlueprintTester,
│                      BlueprintValidator, IssueSeverity, ValidationIssue
├── cli.py             click group `cli`: validate, compile, render, test, diff, generate
├── compiler.py        BlueprintCompiler, CompilationError
├── differ.py          BlueprintDiffer, Change, ChangeType, ChangeSeverity
├── generator.py        BlueprintGenerator
├── loader.py           load_blueprint, load_blueprint_from_str, BlueprintLoadError
├── renderer.py         BlueprintRenderer (to_mermaid, to_markdown)
├── runtime.py          RuntimeGraph (wire_trace/context/compressor/cost_tracker, run())
├── tester.py           BlueprintTester, TestResult
├── validator.py        BlueprintValidator, IssueSeverity, ValidationIssue
└── schema/
    ├── spec.py         BlueprintSpec (root model)
    ├── metadata.py     MetadataSpec (name, version, description, tags, owner)
    ├── providers.py    ProviderBindingSpec (model, provider, fallback_ref)
    ├── agents.py       AgentSpec (prompt, provider, tools, description, guardrails)
    ├── workflows.py    WorkflowSpec (pattern, agents, config, recovery, guardrails),
    │                    RecoverySpec (max_retries, timeout_seconds, fallback_provider)
    ├── contracts.py     ContractSpec (input, output, sla), SLASpec (latency_p95_ms,
    │                    cost_max_usd, quality_min)
    ├── context.py       ContextConfigSpec (memory, compression, redaction),
    │                    MemoryConfig, CompressionConfig, RedactionConfig
    └── observability.py ObservabilitySpec (tracing, cost_budget), TracingConfig,
                          CostBudgetConfig
```

## Confirmed hard runtime coupling

| File | Import | Confirmed |
|---|---|---|
| `compiler.py` | `from pyagent_patterns.base import Agent, MockLLM`<br>`from pyagent_patterns.registry import get_pattern_class` | ✅ lines 7–8 |
| `generator.py` | `from pyagent_patterns.registry import get_pattern_class, list_patterns` | ✅ line 5 |
| `validator.py` | `from pyagent_patterns.registry import list_patterns` | ✅ line 8 |
| `runtime.py` | `TYPE_CHECKING`-only import of `pyagent_patterns.base.{Agent,Pattern,Result}` | ✅ no runtime cost, safe |
| `pyproject.toml` | `pyagent-patterns`, `pyagent-router`, `pyagent-providers`, `pyagent-context` **required** | ⚠️ **correction**: only `pyagent-patterns` is actually imported/required today. `pyagent-router`, `pyagent-providers`, `pyagent-context` are listed as hard dependencies in `pyproject.toml` but **no source file in this package imports them directly** — they're transitive conveniences for consumers who want the full native runtime, not something `compiler.py`/`validator.py`/`generator.py` touch. This still supports the "not a lean manifest" finding, but the *only* import that must move to `adapters/pyagent_adapter.py` is `pyagent_patterns`. |

## CLI commands (actual, not aspirational)

Confirmed: `validate`, `compile`, `render`, `test`, `diff`, `generate`. **`apply`, `simulate`, `dashboard`, `migrate`, `package`, `adapters` do not exist yet** — these were referenced in the mega plan / other docs as future/aspirational commands. `simulate` in particular is used loosely in prior planning docs to mean `test` (contract conformance via MockLLM) — that's the existing `pyagent-blueprint test` command, not a separate one.

## Existing test baseline (frozen as regression net)

`test_cli.py`, `test_compiler.py`, `test_differ.py`, `test_loader.py`, `test_renderer.py`, `test_schema.py`, `test_tester.py`, `test_validator.py`, `test_wire_integration.py` — all present, all pass before this change (baseline).

## Fixtures (actual)

`tests/fixtures/research_agent.yaml` (pipeline pattern), `tests/fixtures/customer_support.yaml` (supervisor pattern, includes `context`, `contracts`, `observability` blocks), `tests/fixtures/invalid_blueprint.yaml`.

## Conclusion / scope adjustment for PR 1

- Proceed with Step 1–3 as planned: extract `compiler.py` → `adapters/pyagent_adapter.py`, keep a deprecated re-export shim, add `test_no_runtime_imports.py`.
- **Adjustment**: only `pyagent-patterns` needs to become an optional extra for the *import-coupling* problem to be solved; `pyagent-router`/`pyagent-providers`/`pyagent-context` were already not imported by core modules, so moving them to extras is a `pyproject.toml`-only change with zero source-code impact — cheaper than the mega plan assumed.
- `validator.py`/`generator.py` both hard-import `pyagent_patterns.registry` — confirmed, Step 5 proceeds as planned.
