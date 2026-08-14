---
description: "PyAgent RuntimeAdapters — the same YAML blueprint compiled and run against five structurally different execution engines (native, LangGraph, CrewAI, OpenAI Agents, Semantic Kernel), all certified against one AdapterConformanceSuite."
---

# Adapters

A `RuntimeAdapter` decides **how** a blueprint runs. The same manifest compiles against five
structurally different adapters today, unmodified — see [Why Blueprint?](../why-blueprint.md) for
the case for declaring **what** a system does separately from **how** it runs.

```yaml
api_version: pyagent/v1
metadata:
  name: customer-support
  version: 1.0.0
providers:
  primary:
    model: gpt-4.1-mini
agents:
  classifier:
    prompt: "Classify into: billing, tech, general"
    provider: primary
  billing:
    prompt: "Handle billing inquiries"
    provider: primary
  tech:
    prompt: "Handle technical support"
    provider: primary
workflows:
  support:
    pattern: supervisor
    agents:
      classifier: classifier
      routes:
        billing: billing
        tech: tech
```

```bash
pyagent-blueprint validate customer-support.yaml
pyagent-blueprint adapters                      # list every registered adapter
pyagent-blueprint test customer-support.yaml     # contract conformance vs. MockLLM, no live API calls
```

Choosing *which* adapter compiles and runs a workflow is a Python-API decision today (the CLI's
`compile` command uses the bundled native runtime by default) — pick an adapter class from
`AdapterRegistry.discover()` and call its `compile()`/`run()` directly:

```python
from pyagent_blueprint.adapter import AdapterRegistry
from pyagent_blueprint.ir import BlueprintIR
from pyagent_blueprint.loader import load_blueprint

spec = load_blueprint("customer-support.yaml")
ir = BlueprintIR.from_spec(spec)

for name in ("langgraph", "crewai", "pyagent"):
    adapter_cls = AdapterRegistry.discover()[name]
    adapter = adapter_cls()
    artifact = adapter.compile(ir)
    result = await adapter.run(artifact, workflow="support", input_="I was charged twice")
```

That's not a hypothetical — it's what the `RuntimeAdapter` conformance suite actually certifies.
Every adapter below implements the same contract (`compile(ir) -> CompiledArtifact`, an always-async
`run()`) and is tested against the same `AdapterConformanceSuite`, which checks compile/run
correctness, diagnostic completeness (governance features are honored or reported via a stable
diagnostic code — never silently dropped), and pattern-intent preservation:

| Adapter | Execution model | What actually runs |
|---|---|---|
| `pyagent` (native) | Full 18-pattern registry | `pyagent_patterns.orchestration.Supervisor` etc. |
| `langgraph` | Declared node/edge graph | Real `StateGraph(...).add_node(...).add_edge(...)`, compiled and invoked |
| `openai_agents` | Handoff/turn-based | Real `Agent` + `Runner.run()` |
| `crewai` | Role-based crew | Real `Agent`/`Task`/`Crew.kickoff_async()` |
| `semantic_kernel` | Event/service-oriented | Real `Kernel` + `ChatCompletionAgent.get_response()` |
| `single_agent` / `sequential_chain` / `state_machine` / `simple_loop` | Zero-dependency reference shapes | Pure stdlib, ships in core |

## Governance diagnostics

Budgets, SLAs, memory tiers, guardrails, recovery policies, and human-in-the-loop checkpoints are
either honored by the adapter or surfaced as a stable `CompileDiagnostic` code (e.g.
`BUDGET_UNSUPPORTED`, `MEMORY_TIER_UNSUPPORTED`, `CHECKPOINT_UNSUPPORTED`) — so you always know,
deterministically, what a given runtime supports, rather than a feature silently doing nothing.

## See also

- [Why Blueprint?](../why-blueprint.md) — the case for declaring what a system does separately from how it runs
- [pyagent-blueprint API Reference](blueprint.md) — `AdapterRegistry`, `RuntimeAdapter`, `CompiledArtifact`
- [pyagent-blueprint vs. LangGraph](../compare/vs-langgraph.md)
- [pyagent-blueprint vs. CrewAI](../compare/vs-crewai.md)
