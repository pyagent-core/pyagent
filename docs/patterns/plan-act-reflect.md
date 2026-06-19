---
description: "The Plan-Act-Reflect loop for token-efficient agent routing in PyAgent: compose ReAct, evaluator-optimizer, and reflection with difficulty-aware model selection and token budgets."
---

# The Plan-Act-Reflect-Repeat Pattern for Token-Efficient Routing

**Plan → Act → Reflect → Repeat** is the iterative loop behind most autonomous agents: plan a step,
take an action (often a tool call), reflect on the result, and decide whether to stop or go again.
PyAgent doesn't bolt this on as a single black box — it composes the loop out of patterns you can
inspect and swap, then makes each turn **token-efficient** with routing and compression.

## The loop, from real building blocks

| Phase | PyAgent pattern |
|-------|-----------------|
| Act + observe (tool use) | [ReAct](../packages/patterns/advanced/react.md) — reason → act → observe |
| Reflect / self-correct | [Self-Reflection](../packages/patterns/resolution/self-reflection.md) |
| Score against criteria, iterate | [Evaluator-Optimizer](../packages/patterns/resolution/evaluator-optimizer.md) |

Each is a real, documented pattern in [`pyagent-patterns`](../packages/patterns/index.md) — so the
loop you build is transparent, not hidden inside a framework primitive.

## Making the loop token-efficient

The expensive part of any repeat loop is paying for a frontier model on *every* turn. PyAgent
addresses that with two layers:

- **Difficulty-aware routing** — [`pyagent-router`](../packages/router.md) scores each step and
  sends easy turns to a cheap model, reserving the strong model for genuinely hard reasoning.
- **Inter-agent compression** — [`pyagent-compress`](../packages/compress.md) trims the context
  passed between turns and enforces a token budget, so a long loop doesn't blow up the prompt.

```python
from pyagent_patterns.advanced import ReAct
from pyagent_router.middleware import RouterMiddleware

router = RouterMiddleware(model_registry={
    "cheap":  AnthropicLLM("claude-haiku-3-5-20241022"),
    "strong": AnthropicLLM("claude-sonnet-4-20250514"),
})
agent = router.wrap(ReAct("researcher", tools=[search, fetch]))
result = await agent.run("Find and summarise the latest pricing changes")
```

## Related reading

- [The Orchestrator-Worker Pattern](orchestrator-worker.md) — when the loop should delegate steps
  to specialists instead of doing them itself.
- [Engineering a Resilient Multi-Agent Harness](../architecture/multi-agent-harness.md) — adding
  guardrails and human checkpoints so a repeat loop can't run away.
