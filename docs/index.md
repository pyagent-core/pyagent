# PyAgent

**18 reusable multi-agent orchestration patterns for LLMs** — with routing, compression, and OTel tracing.

---

## Why PyAgent?

Existing frameworks (LangGraph, CrewAI, AutoGen) give you raw primitives but no **named, tested, composable patterns**. PyAgent fills this gap:

| Feature | LangGraph | CrewAI | AutoGen | **PyAgent** |
|---------|-----------|--------|---------|-------------|
| Named pattern library | ❌ | ❌ | ❌ | ✅ 18 patterns |
| Pattern composition | ❌ | ❌ | ❌ | ✅ |
| Difficulty-aware routing | ❌ | ❌ | ❌ | ✅ |
| Inter-agent compression | ❌ | ❌ | ❌ | ✅ |
| Pattern-aware OTel tracing | ❌ | ❌ | ❌ | ✅ |
| Zero mandatory deps | ❌ | ❌ | ❌ | ✅ |

## Quick Install

```bash
pip install pyagent-patterns  # Core patterns only
pip install pyagent-all       # All 9 packages
```

## Hello World (10 lines)

```python
import asyncio
from pyagent_patterns.base import Agent, MockLLM
from pyagent_patterns.orchestration import Pipeline

llm = MockLLM(responses=["Extracted: key facts", "Summary: concise version"])
pipeline = Pipeline(stages=[
    Agent("extractor", llm),
    Agent("summarizer", llm),
])

result = asyncio.run(pipeline.run("Process this document"))
print(result.output)  # "Summary: concise version"
```

## Packages

| Package | Description |
|---------|-------------|
| **pyagent-patterns** | 18 multi-agent orchestration patterns + composites + guardrails + recovery |
| **pyagent-router** | Difficulty scoring, cost estimation, model selection, routing middleware |
| **pyagent-compress** | Inter-agent message compression, agent pruning, interaction pruning, token budgets |
| **pyagent-trace** | TraceEventBus pub/sub, OpenTelemetry spans, Langfuse export, cost tracking, record/replay |
| **pyagent-providers** | Multi-provider abstraction, registry, routing strategies, fallback chains, capability negotiation, cost optimizer |
| **pyagent-context** | Structured context with trust/sensitivity metadata, three-tier memory (working/session/semantic), compression, retrieval, redaction |
| **pyagent-blueprint** | Declarative YAML specs, Pydantic validation, compilation to RuntimeGraph, contract testing, Mermaid rendering, semantic diff, CLI |
| **pyagent-studio** | CLI + web control plane for designing, simulating, debugging, and governing agent blueprints with live trace streaming |
| **pyagent-all** | Meta-package: installs everything above |

## End-to-End Integration Architecture

```mermaid
flowchart TD
    classDef bp    fill:#7C3AED,stroke:#5B21B6,color:#fff
    classDef exec  fill:#1D4ED8,stroke:#1E40AF,color:#fff
    classDef mem   fill:#059669,stroke:#047857,color:#fff
    classDef obs   fill:#B45309,stroke:#92400E,color:#fff
    classDef sink  fill:#374151,stroke:#1F2937,color:#fff

    subgraph BPL["📋  Blueprint"]
        direction LR
        YAML[/"blueprint.yaml"/]:::bp
        COMP["BlueprintCompiler"]:::bp
        RG["RuntimeGraph"]:::bp
        YAML -->|load + validate| COMP -->|compile| RG
    end

    subgraph EXEC["⚡  Execution"]
        direction LR
        PAT["Patterns\n18 types"]:::exec
        AGT["Agents"]:::exec
        PRV["Providers\nAnthropic · OpenAI · …"]:::exec
        CMP["Compressor\n+ TokenBudget"]:::exec
        PAT -->|orchestrate| AGT -->|call| PRV
    end

    subgraph CTX["🧠  Context & Memory"]
        direction LR
        CL[["ContextLedger"]]:::mem
        WM["Working\nMemory"]:::mem
        SM[("Session\nMemory")]:::mem
        SEM[("Semantic\nMemory")]:::mem
        CL --> WM & SM & SEM
    end

    subgraph OBS["📊  Observability"]
        direction LR
        BUS(["TraceEventBus"]):::obs
        EXP["Console · JSONL\nOTel · Langfuse"]:::sink
        STU["Studio Dashboard\nTraces · Costs · Governance"]:::obs
        BUS --> EXP
        BUS --> STU
    end

    RG -->|"run workflow"| PAT
    AGT <-->|"read / write"| CL
    AGT -->|"compress output"| CMP -->|"trimmed tokens"| AGT
    AGT & PAT & PRV & CMP -.->|"trace events"| BUS
```

**The intended flow for consumers:**

1. **Specify** — Define your agent system in a YAML blueprint (agents, workflows, providers, contracts, observability, context)
2. **Compile** — `BlueprintCompiler` transforms the spec into a `RuntimeGraph` of executable patterns and agents
3. **Orchestrate** — Use design patterns (Pipeline, Supervisor, Debate, etc.) to structure agent collaboration
4. **Provide** — Integrate LLM providers with fallback chains, capability negotiation, and cost optimization
5. **Trace** — Attach a `TraceEventBus` to agents and patterns for observability; events propagate to exporters and Studio
6. **Compress** — Wrap agents with `CompressMiddleware` to reduce inter-agent token transfer; enforce `TokenBudget` limits
7. **Remember** — Use `ContextLedger` with three-tier memory (working → session → semantic) for context persistence across turns
8. **Observe** — Launch Studio to track agent communication, memory compression, context flow, provider costs, and token usage in real time

## Hook-Based Integration

Agents and Patterns support **opt-in hooks** for cross-cutting concerns — zero overhead when not wired:

```python
from pyagent_patterns.base import Agent, MockLLM
from pyagent_trace.events import TraceEventBus
from pyagent_trace import CostTracker
from pyagent_context import ContextLedger
from pyagent_compress import MessageCompressor

agent = (
    Agent("analyst", llm, system_prompt="Analyse data.")
    .set_trace_bus(TraceEventBus())        # emit trace events
    .set_context(ContextLedger())          # read/write context per call
    .set_compressor(MessageCompressor(0.5))# compress output
    .set_cost_tracker(CostTracker())       # track token costs
)

result = await agent.run("What are the key trends?")
# → trace events emitted, context updated, output compressed, cost recorded
```

Or wire all hooks at once via `RuntimeGraph`:

```python
from pyagent_blueprint import load_blueprint, BlueprintCompiler

graph = BlueprintCompiler().compile(load_blueprint("blueprint.yaml"))
graph.wire_trace(bus)
graph.wire_context(ledger)
graph.wire_compressor(compressor)
graph.wire_cost_tracker(tracker)
```

→ See the full [Hooks Guide](guides/hooks.md) and [API & Hooks Bibliography](cookbook/api-bibliography.md).

## Pattern Catalog

### Orchestration (Tier 1)
- [Supervisor](packages/patterns/orchestration/supervisor.md) — classify → route → collect
- [Pipeline](packages/patterns/orchestration/pipeline.md) — sequential stage chain
- [Fan-Out/Fan-In](packages/patterns/orchestration/fan-out-fan-in.md) — parallel + aggregate
- [Hierarchical](packages/patterns/orchestration/hierarchical.md) — manager → teams → workers
- [Orchestrator-Workers](packages/patterns/orchestration/orchestrator-workers.md) — dynamic delegation

### Resolution (Tier 2)
- [Self-Reflection](packages/patterns/resolution/self-reflection.md) — generate → critique → refine
- [Cross-Reflection](packages/patterns/resolution/cross-reflection.md) — peer review
- [Debate](packages/patterns/resolution/debate.md) — adversarial argumentation + judge
- [Voting](packages/patterns/resolution/voting.md) — majority consensus
- [Evaluator-Optimizer](packages/patterns/resolution/evaluator-optimizer.md) — criteria-based optimization

### Structural (Tier 3)
- [Role-Based](packages/patterns/structural/role-based.md) — specialized agent roles
- [Layered](packages/patterns/structural/layered.md) — abstraction layers
- [Topology](packages/patterns/structural/topology.md) — chain / star / mesh
- [Blackboard](packages/patterns/structural/blackboard.md) — shared async state

### Advanced (Tier 4)
- [Talker-Reasoner](packages/patterns/advanced/talker-reasoner.md) — fast System 1 / slow System 2
- [Swarm](packages/patterns/advanced/swarm.md) — emergent behavior
- [Human-in-the-Loop](packages/patterns/advanced/human-in-the-loop.md) — approval gates
- [ReAct](packages/patterns/advanced/react.md) — reason → act → observe
