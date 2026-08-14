---
description: "ADR: Pipeline vs Supervisor — when a multi-agent task has fixed sequential stages vs distinct categories needing specialist routing."
---

# ADR: Pipeline vs. Supervisor

**Status:** Accepted — both are named `pyagent-patterns` shapes with distinct, non-overlapping
`use_when` conditions.

## Context

Both patterns run more than one agent in a coordinated way, and both are common defaults teams
reach for without checking whether the task's actual shape matches. Picking wrong doesn't fail
loudly — it just produces an awkward implementation (a `Supervisor` classifying into one branch
every time, or a `Pipeline` with a stage that's really a conditional).

## Decision

**Use Pipeline when the task has clear sequential stages, and every input goes through the same
stages in the same order** — ETL, document processing, multi-step transformation. Cost: N LLM
calls (one per stage); latency is the sum of all stages, since each depends on the previous one's
output.

**Use Supervisor when tasks fall into distinct categories, and a category-specific specialist is
meaningfully better than a generalist** — customer support triage, multi-domain Q&A. Cost: 2–3 LLM
calls (classify → specialist → optional formatter); latency is lower than Pipeline for the same
apparent complexity, since only one specialist branch executes per input, not every stage.

The distinguishing question: **does every input need the same sequence of steps (Pipeline), or does
the right sequence depend on what kind of input it is (Supervisor)?**

## Consequences

- Picking Pipeline for a categorization task means every input pays for every stage even when most
  stages are irrelevant to it — wasted cost and latency.
- Picking Supervisor for a strictly sequential task means building an artificial classifier whose
  only job is to always route to the same place — wasted complexity for zero benefit.
- If tasks are neither purely sequential nor purely categorical — subtasks aren't known until the
  goal is analyzed — neither pattern fits; see
  [Orchestrator-Workers](../../packages/patterns/orchestration/orchestrator-workers.md) instead.

See the [pattern catalog](../../packages/patterns/index.md) for the full comparison table and
[patterns.json](../../patterns.json) for the machine-readable `use_when`/`avoid_when` for both.
