---
description: "What is multi-agent orchestration? A definition, with the coordination patterns (pipelines, supervisors, debate, voting) that make it work in production LLM systems."
---

# What is multi-agent orchestration?

**Multi-agent orchestration** is the practice of coordinating multiple specialized LLM-driven agents
— each with a narrower scope than a single do-everything prompt — so they combine into a system that
solves a task no individual agent handles well alone. The orchestration layer is the code (or
manifest) that decides which agent runs when, what data passes between them, and how failures,
budgets, and human review are handled.

## Why not one large prompt?

A single, monolithic prompt asked to classify a request, look things up, reason about them, and
format a polished answer tends to underperform a set of smaller agents each doing one of those things
well — smaller prompts are easier to test, cheaper to run on a weaker model, and easier to debug when
something goes wrong, because failures are localized to one step instead of buried in one giant
completion.

## The core coordination patterns

Most multi-agent systems reduce to a handful of recurring shapes. `pyagent-patterns` names 18 of
them, grouped into four families:

- **Orchestration** — a controller directs specialist workers: `Supervisor` (classify → route →
  specialist), `Pipeline` (linear stages), `Fan-Out / Fan-In` (parallel workers, merged), `Hierarchical`,
  `Orchestrator-Workers`.
- **Resolution** — multiple agents converge on a better answer: `Self-Reflection`, `Cross-Reflection`,
  `Debate`, `Voting`, `Evaluator-Optimizer`.
- **Structural** — the topology itself carries meaning: `Role-Based`, `Layered`, `Topology`,
  `Blackboard`.
- **Iterative & Advanced** — looping or emergent coordination: `ReAct`, `Talker-Reasoner`, `Swarm`,
  `Human-in-the-Loop`.

See the full [Design Patterns](../packages/patterns/index.md) catalog for runnable examples of each.

## What production orchestration needs beyond "wire some agents together"

A prototype can hard-code which agent calls which. A production system additionally needs:

- **Provider routing** — which model handles which agent, with fallbacks (`providers` +
  `pyagent-router`).
- **Governed memory** — shared context with trust tiers, expiry, and redaction, not an unbounded
  transcript (`ContextLedger`).
- **Budgets and SLAs** — declared cost/latency ceilings, not implicit ones.
- **Guardrails and recovery** — retries, timeouts, and fallback providers when a step fails.
- **Observability** — tracing every call and cost across the whole system, not just one agent.
- **Human-in-the-loop checkpoints** — a workflow-level pause for approval, not just a single
  tool-confirmation prompt.

## Declaring orchestration instead of hand-wiring it

`pyagent-blueprint` lets you declare all of the above — agents, the named pattern wiring them
together, providers, contracts, and observability — in one YAML manifest, validated statically and
compiled onto any registered runtime. See [What is an agent blueprint?](agent-blueprint.md) and
[Why Blueprint?](../why-blueprint.md) for how that works in practice.
