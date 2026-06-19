---
description: "The Orchestrator-Worker pattern for multi-agent orchestration: split a monolithic LLM prompt into a supervising orchestrator and specialized worker agents, with difficulty-aware routing and token budgets."
---

# The Orchestrator-Worker Pattern in Multi-Agent Orchestration

The **Orchestrator-Worker** pattern replaces one overloaded, do-everything prompt with a
supervising **orchestrator** that decomposes a task and delegates each part to a specialized
**worker** agent. It is the workhorse of reliable [multi-agent orchestration](../packages/patterns/index.md):
each worker has a narrow remit, so its prompt is shorter, its output is easier to validate, and a
failure is contained to one step instead of corrupting the whole run.

PyAgent ships this pattern directly — see the reference page for
[Orchestrator-Workers](../packages/patterns/orchestration/orchestrator-workers.md) and the closely
related [Supervisor](../packages/patterns/orchestration/supervisor.md) pattern.

## When to reach for it

- A single prompt is doing classification **and** retrieval **and** drafting **and** review.
- Different sub-tasks need different models (a cheap model to triage, an expensive one to reason).
- You need per-step validation or guardrails rather than one opaque generation.

## How it works in PyAgent

```python
from pyagent_patterns.orchestration import Supervisor
from pyagent_patterns.base import Agent
from pyagent_providers import AnthropicLLM

orchestrator = Agent("router", AnthropicLLM("claude-haiku-3-5-20241022"))
workers = {
    "billing":   Agent("billing",   AnthropicLLM("claude-sonnet-4-20250514")),
    "technical": Agent("technical", AnthropicLLM("claude-sonnet-4-20250514")),
}

supervisor = Supervisor(orchestrator=orchestrator, workers=workers)
result = await supervisor.run("My invoice double-charged me last month")
```

The orchestrator classifies the request and routes it to exactly one worker. Because routing is
explicit, you can layer **difficulty-aware model selection** with
[`pyagent-router`](../packages/router.md) (cheap model for easy tasks, strong model for hard ones)
and enforce **token budgets** across the hand-off with
[`pyagent-compress`](../packages/compress.md).

## Related reading

- [Engineering a Resilient Multi-Agent Harness](../architecture/multi-agent-harness.md) — wrapping
  orchestrator-worker graphs with guardrails, recovery, and human checkpoints.
- [Agent Experience Optimization (AXO)](../concepts/agent-experience-optimization.md) — why
  narrow, well-described workers are easier for autonomous agents to consume.
- [Hierarchical](../packages/patterns/orchestration/hierarchical.md) — multi-level orchestration when
  one layer of workers isn't enough.
