---
description: "The Execution & Routing pillar of PyAgent's architecture — 18 orchestration patterns, difficulty-aware model routing, multi-provider fallback, and token budgets. What it solves, when to use it, and when not to."
---

# Execution & Routing

**Verb: Execute.** Four independently installable packages: `pyagent-patterns`, `pyagent-router`,
`pyagent-providers`, `pyagent-compress`. None require Blueprint, Context, or Observability.

## What it solves

Running more than one agent raises questions hand-written loops answer inconsistently every time:
how do agents hand off to each other (a named, testable pattern vs. ad-hoc glue code), which model
handles which task (a fixed choice vs. cost-aware routing), what happens when a provider is down
(a crash vs. a fallback chain), and how message history stays within budget on long runs.

## When to use

- More than one agent, with a real coordination need between them — routing, review, debate,
  parallel dispatch. See the [pattern catalog](../packages/patterns/index.md) for all 18 named
  shapes and their individual `use_when`/`avoid_when`.
- Cost varies meaningfully by task difficulty and you want cheap tasks on cheap models
  automatically (`pyagent-router`).
- You have 2+ interchangeable providers and want automatic fallback or cost/latency/capability-based
  routing between them (`pyagent-providers`).
- Long-running sessions are approaching a token budget (`pyagent-compress`).

## When not to use

- A single agent, single call, nothing to hand off to — see
  [why-blueprint.md](../why-blueprint.md#when-you-dont-need-pyagent-at-all) and the pattern catalog's
  own [note on when no pattern applies](../packages/patterns/index.md#pattern-selection-guide).
- Only one model/provider is ever used — `pyagent-router` and `pyagent-providers`' routing add
  indirection with nothing to select between.
- History never approaches a token budget — `pyagent-compress` is pure overhead.

## Tradeoffs

Named patterns are a real constraint: they cover the 18 documented shapes, not arbitrary dynamic
control flow. Difficulty-based routing (`pyagent-router`) is heuristic by default — its accuracy
caps whatever routes on top of it. Fallback chains (`pyagent-providers`) can silently degrade
quality if a fallback provider has different capabilities than the primary, without monitoring.

## Packages

- `pip install pyagent-patterns` — 18 patterns, zero dependencies, async-first.
- `pip install pyagent-router` — `DifficultyScorer`, `ModelSelector`, `CostEstimator`.
- `pip install pyagent-providers` — `ProviderRegistry`, `ProviderRouter`, `FallbackChain`,
  `CapabilityNegotiator`, `CostOptimizer`.
- `pip install pyagent-compress` — `TokenBudget`, `MessageCompressor`, `AgentPruner`,
  `InteractionPruner`.

## Example

```python
from pyagent_patterns import Supervisor

result = await Supervisor(
    classifier=classifier_agent,
    routes={"billing": billing_agent, "tech": tech_agent},
).run("I was charged twice")
```

See the [Router guide](../guides/router.md), [Providers guide](../guides/providers.md), and
[Compression guide](../guides/compression.md) for full detail on each package.

## Related pillars

Execution's patterns can be declared inside a [Blueprint](blueprint.md) `workflows:` block instead
of written in Python. Agents in a run can share state via [Context & Memory](context.md). Every
pattern and adapter emits events consumable by [Observability](observability.md) — none of that
integration is required to use the patterns standalone.
