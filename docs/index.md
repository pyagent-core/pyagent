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
pip install pyagent-all       # All 4 packages
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
| **pyagent-patterns** | 18 patterns + composites + guardrails + recovery |
| **pyagent-router** | Difficulty scoring + cost estimation + model selection |
| **pyagent-compress** | Message compression + agent pruning + token budgets |
| **pyagent-trace** | OTel spans + cost tracking + record/replay |

## Pattern Catalog

### Orchestration (Tier 1)
- [Supervisor](patterns/orchestration/supervisor.md) — classify → route → collect
- [Pipeline](patterns/orchestration/pipeline.md) — sequential stage chain
- [Fan-Out/Fan-In](patterns/orchestration/fan-out-fan-in.md) — parallel + aggregate
- [Hierarchical](patterns/orchestration/hierarchical.md) — manager → teams → workers
- [Orchestrator-Workers](patterns/orchestration/orchestrator-workers.md) — dynamic delegation

### Resolution (Tier 2)
- [Self-Reflection](patterns/resolution/self-reflection.md) — generate → critique → refine
- [Cross-Reflection](patterns/resolution/cross-reflection.md) — peer review
- [Debate](patterns/resolution/debate.md) — adversarial argumentation + judge
- [Voting](patterns/resolution/voting.md) — majority consensus
- [Evaluator-Optimizer](patterns/resolution/evaluator-optimizer.md) — criteria-based optimization

### Structural (Tier 3)
- [Role-Based](patterns/structural/role-based.md) — specialized agent roles
- [Layered](patterns/structural/layered.md) — abstraction layers
- [Topology](patterns/structural/topology.md) — chain / star / mesh
- [Blackboard](patterns/structural/blackboard.md) — shared async state

### Advanced (Tier 4)
- [Talker-Reasoner](patterns/advanced/talker-reasoner.md) — fast System 1 / slow System 2
- [Swarm](patterns/advanced/swarm.md) — emergent behavior
- [Human-in-the-Loop](patterns/advanced/human-in-the-loop.md) — approval gates
- [ReAct](patterns/advanced/react.md) — reason → act → observe
