---
description: "The Observability pillar of PyAgent's architecture — pattern-aware OpenTelemetry tracing, cost tracking, record/replay, and a web dashboard. What it solves, when to use it, and when not to."
---

# Observability

**Verb: Observe.** Two independently installable packages: `pyagent-trace` and `pyagent-studio`.

## What it solves

A multi-agent run that fails or costs more than expected is hard to debug from logs alone — you
need to know which agent produced which output, what it cost, and ideally be able to replay the
exact sequence of events. Generic OpenTelemetry gives you spans; it doesn't know a `Supervisor`
pattern's parent/child structure unless something teaches it that.

## When to use

- You need distributed tracing that reflects the pattern's actual structure (e.g.
  supervisor → workers), not a flat call list.
- You need running cost totals across a traced run, not just per-call estimates.
- You need to reproduce a specific run's exact sequence of events for debugging (record/replay).
- You want a visual way to inspect traces, diff blueprint revisions, and check provider health,
  rather than reading raw CLI/JSON output (`pyagent-studio`'s dashboard).

## When not to use

- **Full observability is excessive** for a single-agent, single-call workflow, or for early
  prototyping where the system's shape changes every few minutes — the tracing setup and span
  review overhead outweighs what there is to observe. Start with `console` output during
  development; add `otel`/`langfuse` export once the system is stable enough that tracing pays for
  itself.
- A flat list of calls is already sufficient — pattern-aware spans (`PatternSpanEmitter`) add
  structure a simple linear script doesn't need.
- Live/aggregate observability is all you need — the heavier `Recorder`/replay path is for
  reproducing a *specific* run, not ongoing monitoring.

## Tradeoffs

Exporters have real tradeoffs, not just feature differences: `console` is zero-setup but nothing
persists; `jsonl` is durable but nothing consumes it live; `otel` is vendor-neutral but needs a
running collector; `langfuse` gives LLM-specific views but ties you to Langfuse. Cost tracking
depends on accurate per-provider pricing data to stay trustworthy as providers change pricing.

## Packages

- `pip install pyagent-trace` — `TraceEventBus`, `Recorder`, `CostTracker`, `PatternSpanEmitter`,
  exporters (`console`, `jsonl`, `otel`, `langfuse`).
- `pip install pyagent-studio` — CLI + FastAPI/HTMX web dashboard (trace explorer, blueprint diff
  view, governance/compliance view).

## Example

```python
from pyagent_trace import traced_pattern
from pyagent_trace.exporters.otel import OTelExporter

@traced_pattern(exporter=OTelExporter())
async def run_support_workflow(task: str) -> str:
    ...
```

See the [Tracing guide](../guides/tracing.md) and [Studio guide](../guides/studio.md) for the full
API and dashboard walkthrough.

## Related pillars

Observability instruments [Execution & Routing](index.md#execution-routing) patterns and adapters automatically
once wired in, and can be declared inside a [Blueprint](blueprint.md)'s `observability:` block.
Context-tier changes and redaction events are traceable too — none of that integration is required
to use tracing standalone.
