# Tracing Guide

**pyagent-trace** provides pattern-aware OpenTelemetry spans for full observability.

## Architecture

```mermaid
flowchart LR
    P[Pattern.run] --> S[Span Emitter]
    S --> OT[OpenTelemetry SDK]
    OT --> B1[Jaeger]
    OT --> B2[Langfuse]
    OT --> B3[Grafana Tempo]
    OT --> B4[Datadog]

    subgraph Span Attributes
        PT[pattern.type]
        AR[agent.name]
        CT[cost.total_usd]
        DR[exec.duration_ms]
    end
```

## Quick Start

### Decorators (Simplest)

```python
from pyagent_trace import traced_pattern, traced_agent
from pyagent_patterns.base import Agent, MockLLM
from pyagent_patterns.orchestration import Pipeline

# Auto-emit spans for every pattern.run()
@traced_pattern
class TracedPipeline(Pipeline):
    pass

# Or wrap individual agents
agent = traced_agent(Agent("my_agent", my_llm))
```

### Manual Span Control

```python
from pyagent_trace import PatternSpanEmitter

emitter = PatternSpanEmitter()
span = emitter.pattern_span("debate", {"rounds": 3})
try:
    result = await pattern.run(task)
    emitter.set_pattern_result(span, len(result.output), rounds=3, cost_estimate=0.012)
finally:
    span.end()
```

## Cost Tracking

```python
from pyagent_trace import CostTracker

tracker = CostTracker()
tracker.record("debate", "bull_agent", "gpt-4o", input_tokens=500, output_tokens=200, cost_usd=0.003)
tracker.record("debate", "bear_agent", "gpt-4o-mini", input_tokens=500, output_tokens=200, cost_usd=0.0004)
tracker.record("debate", "judge", "gpt-4o", input_tokens=1000, output_tokens=300, cost_usd=0.0055)

print(f"Total: ${tracker.total_cost:.4f}")
print(f"By pattern: {tracker.by_pattern()}")
print(f"By model: {tracker.by_model()}")
```

## Record & Replay

```python
from pyagent_trace.recorder import Recorder

# Record
recorder = Recorder()
recorder.start("debate")
recorder.record_llm_call("bull", messages, response_text)
recorder.end(result.output)
recorder.save("traces/debate_run_001.jsonl")

# Replay / Debug
entries = Recorder.load("traces/debate_run_001.jsonl")
for entry in entries:
    print(f"[{entry.event_type}] {entry.agent_name}: {entry.response[:80]}...")
```

## Custom Attributes

All attributes are namespaced under `pyagent.*`:

| Attribute | Type | Description |
|-----------|------|-------------|
| `pyagent.pattern.type` | string | Pattern name (e.g., "debate") |
| `pyagent.pattern.rounds` | int | Number of rounds executed |
| `pyagent.agent.name` | string | Agent name |
| `pyagent.router.difficulty` | int | Task difficulty 1-10 |
| `pyagent.router.selected_model` | string | Routed model name |
| `pyagent.compress.savings_pct` | float | Compression savings 0-1 |
| `pyagent.cost.total_usd` | float | Total cost in USD |
| `pyagent.exec.duration_ms` | float | Execution time in ms |
