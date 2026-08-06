---
description: "Why pyagent-blueprint? Declare a multi-agent system once in YAML and run it on any registered runtime adapter — proven against five structurally different execution models, from LangGraph's state graphs to CrewAI's role-based crews."
---

# Why Blueprint?

Most multi-agent frameworks make you choose your runtime *before* you design your system: a
LangGraph `StateGraph`, a CrewAI `Crew`, an AutoGen conversation. The orchestration logic and the
execution engine are the same lines of Python — which means every migration, every framework
evaluation, and every "let's also support X" request means rewriting the system from scratch.

`pyagent-blueprint` separates the two. You declare **what** your system does — agents, workflows,
providers, contracts, governance — in a single YAML manifest. A `RuntimeAdapter` decides **how** it
runs. The same manifest compiles against five structurally different adapters today, unmodified.

!!! note "How this relates to the homepage comparison"
    The [homepage](index.md) compares PyAgent's overall feature set against LangChain, CrewAI, and
    AutoGen (pattern count, routing, memory, and more). This page and the pages under it go one
    layer deeper on a single, specific claim from that table — the YAML-vs-code tradeoff and
    cross-runtime portability — with real adapter code, not just a feature checklist.

## The same manifest, five runtimes

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

## What you get that hand-written orchestration code doesn't

- **Diff and review like infrastructure.** `pyagent-blueprint diff old.yaml new.yaml` produces a
  semantic diff over the IR — not a text diff of hand-wired Python — so a PR reviewer can see
  exactly which agent, route, or SLA changed.
- **Validate before you run anything.** Static analysis (dangling references, schema violations)
  catches mistakes before an LLM call is ever made.
- **Governance is never silently dropped.** Budgets, SLAs, memory tiers, guardrails, recovery
  policies, and human-in-the-loop checkpoints are either honored by the adapter or surfaced as a
  stable `CompileDiagnostic` code (e.g. `BUDGET_UNSUPPORTED`, `MEMORY_TIER_UNSUPPORTED`,
  `CHECKPOINT_UNSUPPORTED`) — so you always know, deterministically, what a given runtime supports.
- **Package and test without live API calls.** `pyagent-blueprint test` (contract conformance) and
  `pyagent-blueprint package` (Agent Unit archives) both work against a `MockLLM`, so CI can validate
  a system's shape before spending a token.
- **Zero mandatory runtime dependency.** Core `pyagent-blueprint` depends only on `pydantic`,
  `pyyaml`, and `click`. You install a runtime adapter — the bundled `pyagent` reference stack, one
  of four zero-dependency stdlib adapters, or a third-party package — only when you're ready to run.

## When a blueprint *isn't* the right fit

To be direct about the tradeoff: if your orchestration logic depends on dynamic, runtime-computed
control flow that can't be expressed as a static graph (e.g. an agent that decides to spin up an
arbitrary number of sub-agents based on a live computation), hand-written code in your chosen
framework is still the right tool. Blueprint's IR models agents, typed workflows, and named
patterns — it's declarative by design, and that's a real constraint, not just a feature.

See the pattern-specific comparisons for how this plays out against real frameworks:

- [pyagent-blueprint vs. LangGraph](compare/vs-langgraph.md)
- [pyagent-blueprint vs. CrewAI](compare/vs-crewai.md)
- [pyagent-blueprint vs. AutoGen](compare/vs-autogen.md)

Or start from the concepts: [What is an agent blueprint?](concepts/agent-blueprint.md) and
[What is multi-agent orchestration?](concepts/multi-agent-orchestration.md)
