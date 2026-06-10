# pyagent-trace

**Pattern-aware OpenTelemetry tracing** for multi-agent LLM systems. Track costs, record interactions, debug with replay.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](../../LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

## Install

```bash
pip install pyagent-trace              # Core (CostTracker, Recorder work without OTel)
pip install pyagent-trace[otel]        # With OpenTelemetry spans
```

Depends on: `pyagent-patterns`. OTel features require `opentelemetry-api` + `opentelemetry-sdk`.

## CostTracker — Track Costs Across a Workflow

Works without OpenTelemetry. Accumulates costs and provides breakdowns by pattern, agent, and model.

```python
from pyagent_trace import CostTracker

tracker = CostTracker()

# Record costs (pattern, agent, model, input_tokens, output_tokens, cost_usd)
tracker.record("pipeline", "extractor", "gpt-4o-mini", 500, 200, 0.00019)
tracker.record("pipeline", "analyst", "gpt-4o", 800, 400, 0.00600)
tracker.record("supervisor", "classifier", "claude-haiku-3.5", 200, 50, 0.00018)
tracker.record("supervisor", "specialist", "claude-sonnet-4", 1200, 600, 0.01260)

print(f"Total: ${tracker.total_cost:.5f}")  # $0.01897
print(f"Tokens: {tracker.total_tokens}")    # 3950

# Breakdowns
print(tracker.by_pattern())  # {"pipeline": 0.00619, "supervisor": 0.01278}
print(tracker.by_agent())    # {"extractor": 0.00019, "analyst": 0.00600, ...}
print(tracker.by_model())    # {"gpt-4o-mini": 0.00019, "gpt-4o": 0.00600, ...}

print(tracker.summary())
# {
#     "total_cost_usd": 0.01897,
#     "total_tokens": 3950,
#     "entries": 4,
#     "by_pattern": {...},
#     "by_agent": {...},
#     "by_model": {...}
# }
```

## Recorder — Record and Replay Pattern Executions

Serialises all messages and LLM responses to JSONL for debugging and replay. Works without OpenTelemetry.

```python
from pyagent_trace import Recorder
from pyagent_patterns.base import Message

recorder = Recorder()
recorder.start("debate")

# Record LLM calls as they happen
recorder.record_llm_call(
    agent_name="bull_debater",
    messages=[Message.user("Argue the bull case for NVDA")],
    response="Strong data center growth driven by AI training demand...",
    metadata={"round": 1, "model": "gemini-2.5-flash"},
)

recorder.record_llm_call(
    agent_name="bear_debater",
    messages=[Message.user("Argue the bear case for NVDA")],
    response="Valuation stretched at 65x PE, customer concentration risk...",
    metadata={"round": 1, "model": "gemini-2.5-flash"},
)

recorder.end("Buy for initial launch, plan migration in 18 months")

# Save full trace to disk
recorder.save("traces/debate_nvda_2025-11-15.jsonl")

# Load and inspect later
entries = Recorder.load("traces/debate_nvda_2025-11-15.jsonl")
for entry in recorder.llm_calls:
    print(f"[{entry.agent_name}] → {entry.response[:80]}...")
    print(f"  Metadata: {entry.metadata}")
```

## @traced_pattern — Auto-Trace a Pattern Class

Requires `pip install pyagent-trace[otel]`. Wraps every `.run()` call with an OTel span.

```python
from pyagent_trace import traced_pattern
from pyagent_patterns.orchestration import Pipeline
from pyagent_patterns.resolution import Debate

# Decorate the class
@traced_pattern
class TracedPipeline(Pipeline):
    pass

# Or apply to an existing class
TracedDebate = traced_pattern(Debate)

# Configure your OTel exporter (Jaeger, Honeycomb, Grafana Tempo, OTLP...)
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

provider = TracerProvider()
provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint="http://localhost:4317")))
trace.set_tracer_provider(provider)

# Now all runs emit spans automatically
pipeline = TracedPipeline(stages=[...])
result = asyncio.run(pipeline.run("My task"))
# → OTel span: "pyagent.pattern.pipeline"
#   attributes: pyagent.pattern.type, pyagent.exec.duration_ms,
#               pyagent.exec.token_estimate, pyagent.cost.total_usd
```

## traced_agent — Trace Individual Agents

```python
from pyagent_trace import traced_agent
from pyagent_patterns.base import Agent

agent = traced_agent(Agent("analyst", llm, system_prompt="Analyse data."))
# Every agent.run() now emits a "pyagent.agent.analyst" span
```

## PatternSpanEmitter — Manual Span Control

For custom patterns and workflows where you need explicit span management.

```python
from pyagent_trace import PatternSpanEmitter

emitter = PatternSpanEmitter()

# Emit a span for a custom pattern
span = emitter.pattern_span("custom_workflow", attributes={"workflow.version": "2.0"})

# Nested agent span
agent_span = emitter.agent_span("my_agent", parent_span=span)
# ... run agent ...
agent_span.end()

# Record result on the parent span
emitter.set_pattern_result(
    span=span,
    output_length=1240,
    rounds=3,
    duration_ms=4200.0,
    token_estimate=3500,
    cost_estimate=0.0045,
)

# Record routing decision
emitter.set_routing_info(
    span=span,
    difficulty=7,
    selected_model="claude-sonnet-4",
    cost_estimate=0.0038,
    category="hard",
)

# Record compression savings
emitter.set_compression_info(
    span=span,
    input_tokens=2000,
    output_tokens=950,
    savings_pct=0.525,
)

span.end()
```

## PyAgentAttributes Reference

All custom attributes are namespaced under `pyagent.*`:

| Attribute | Type | Description |
|-----------|------|-------------|
| `pyagent.pattern.type` | str | Pattern name (pipeline, debate, etc.) |
| `pyagent.pattern.rounds` | int | Number of rounds executed |
| `pyagent.agent.name` | str | Agent name |
| `pyagent.exec.duration_ms` | float | Execution time in milliseconds |
| `pyagent.exec.token_estimate` | int | Estimated total tokens |
| `pyagent.cost.total_usd` | float | Estimated total cost in USD |
| `pyagent.router.difficulty` | int | Task difficulty score (1–10) |
| `pyagent.router.model` | str | Selected model name |
| `pyagent.router.category` | str | Difficulty category (easy/medium/hard) |
| `pyagent.compress.input_tokens` | int | Tokens before compression |
| `pyagent.compress.output_tokens` | int | Tokens after compression |
| `pyagent.compress.savings_pct` | float | Compression savings (0.0–1.0) |

## OTel Exporter Configuration Examples

### OTLP (Jaeger, Grafana Tempo, Honeycomb)

```python
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
exporter = OTLPSpanExporter(endpoint="http://localhost:4317")
```

### Console (development/debugging)

```python
from opentelemetry.sdk.trace.export import ConsoleSpanExporter
exporter = ConsoleSpanExporter()
```

### Honeycomb

```python
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
exporter = OTLPSpanExporter(
    endpoint="https://api.honeycomb.io/v1/traces",
    headers={"x-honeycomb-team": "YOUR_API_KEY"},
)
```

## Full Documentation

See [pyagent.dev](https://pyagent.dev) for full API reference and integration guides.
