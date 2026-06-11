# Studio — Traces

Studio's trace explorer loads `.jsonl` files produced by `pyagent-trace`'s `Recorder`. Every LLM call, agent step, and workflow run is recorded as a structured span — Studio lets you browse, filter, and analyse them visually.

---

## Recording Traces

Traces are recorded by `pyagent-trace`. Wire it up in your blueprint:

```yaml
observability:
  tracing:
    enabled: true
    record_to: traces/production_runs.jsonl
```

Or in Python:

```python
from pyagent_trace.recorder import Recorder
from pyagent_trace.events import TraceEventBus

bus      = TraceEventBus()
recorder = Recorder(bus, output_path="traces/runs.jsonl")

# Attach to a compiled graph
graph.wire_trace(bus)
```

Each LLM call emits two events: `llm_call_start` and `llm_call_end` (or `llm_call_error`).

---

## Span Format

Each line in the `.jsonl` file is a JSON object:

```json
{
  "event_type": "llm_call_end",
  "agent_name": "billing_agent",
  "workflow": "main",
  "pattern": "supervisor",
  "run_id": "run-174",
  "provider": "anthropic",
  "model": "claude-sonnet-4-20250514",
  "input_tokens": 180,
  "output_tokens": 140,
  "duration_ms": 2401.3,
  "cost_estimate": 0.00840,
  "timestamp": "2025-06-09T14:32:01.243Z"
}
```

---

## Loading in the Dashboard

```bash
# Load on startup
pyagent dashboard --trace traces/production_runs.jsonl

# Or upload via the /traces page in the UI
```

The dashboard shows:

```
traces/production_runs.jsonl — 1,240 spans from 180 runs

Run #174   supervisor   3 steps   3.4s   $0.0092
├── classifier     0.3s  claude-haiku   12→1 tok    $0.00001
├── billing_agent  2.4s  claude-sonnet  180→140 tok $0.00840
└── formatter      0.7s  claude-haiku   145→80 tok  $0.00051

Run #173   supervisor   3 steps   1.1s   $0.0021
├── classifier     0.3s  claude-haiku   11→1 tok    $0.00001
├── technical_agent 0.6s  gpt-4o-mini  95→110 tok  $0.00019
└── formatter      0.2s  claude-haiku   120→60 tok  $0.00040
```

---

## Cost Analysis View

```
Cost by model (last 7 days)

claude-sonnet-4-20250514   ████████████████  $24.80 (72%)
gpt-4o-mini               ████               $6.20  (18%)
claude-haiku-3-5-20241022  ██                $3.40  (10%)

Cost by workflow
  main   $31.20 (89 runs)    avg: $0.35/run
  quick  $3.20  (91 runs)    avg: $0.035/run

Daily spend
  2025-06-09  $4.12  ████
  2025-06-08  $3.98  ████
  2025-06-07  $5.43  █████
```

---

## Python API

Use `TraceService` directly to load and query spans:

```python
from pyagent_studio.services.trace_service import TraceService

svc   = TraceService()
spans = svc.load("traces/production_runs.jsonl")
print(f"Loaded {len(spans)} spans")

# Filter by event type
llm_calls = svc.query(event_type="llm_call_end")

# Filter by agent
billing_spans = svc.query(agent_name="billing_agent")

# Filter by duration — find slow calls
slow = svc.query(min_duration_ms=2000)
for s in slow:
    print(f"{s.agent_name} ({s.model}): {s.duration_ms:.0f}ms, ${s.cost_estimate:.5f}")

# Aggregate cost per model
from collections import defaultdict
cost_by_model: dict[str, float] = defaultdict(float)
for s in llm_calls:
    cost_by_model[s.model] += s.cost_estimate or 0

for model, cost in sorted(cost_by_model.items(), key=lambda x: -x[1]):
    print(f"{model}: ${cost:.4f}")
```

---

## Trace Streaming (SSE)

When `pyagent-trace` is running alongside Studio, spans are streamed to the dashboard in real time via Server-Sent Events — no page refresh required. The `/traces` endpoint emits one `data:` line per span as it arrives.

```python
# Studio's SSE endpoint (used by the browser automatically)
# GET /traces/stream   → text/event-stream
```

---

## See Also

- [Trace Package](../../packages/trace.md) — `Recorder`, `TraceEventBus`, span types
- [Services](services.md#traceservice) — `TraceService` API reference
- [Dashboard](dashboard.md#traces) — visual trace explorer
