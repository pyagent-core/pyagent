---
description: "ADR: Supervisor vs Orchestrator-Workers — routing to a known set of specialists vs dynamically planning subtasks that aren't known upfront."
---

# ADR: Supervisor vs. Orchestrator-Workers

**Status:** Accepted.

## Context

Both patterns involve a coordinating agent directing work to other agents. The difference is
whether the set of "other agents" and their assignments is known in advance or has to be figured
out per-task.

## Decision

**Use Supervisor when the categories are fixed and known in advance** — a classifier routes each
input to one of N known specialists. Cost: 2–3 LLM calls total.

**Use Orchestrator-Workers when subtasks aren't known until the goal is analyzed, and the worker
pool has meaningfully different specializations the planner assigns dynamically** — open-ended
goals like "research this topic" where the number and nature of sub-questions depends on the topic
itself. Cost: 1 planning call + N worker calls (N is dynamic, decided by the planner) + 1 synthesis
call.

The distinguishing question: **can you enumerate the routing categories before seeing the input
(Supervisor), or does the input itself determine how many workers are needed and what they should
do (Orchestrator-Workers)?**

## Consequences

- Supervisor with an unbounded/unknown category set forces an awkward "other" bucket that absorbs
  everything the classifier can't confidently place — a symptom of the wrong pattern, not a tuning
  problem.
- Orchestrator-Workers for a fixed-category task pays for a planning call that will produce the
  same plan every time — pure overhead versus Supervisor's direct classify-and-route.
- Orchestrator-Workers' dynamic worker count makes cost and latency less predictable than
  Supervisor's fixed 2–3 calls — a real operational tradeoff if you need tight cost bounds.
- If workers need to communicate directly with each other rather than only report to the
  coordinator, neither pattern fits — see
  [Blackboard](../../packages/patterns/structural/blackboard.md) or
  [Swarm](../../packages/patterns/advanced/swarm.md) instead.

See the [pattern catalog](../../packages/patterns/index.md) for the full comparison and
[patterns.json](../../patterns.json) for machine-readable `use_when`/`avoid_when`.
