# pyagent-trace

**Pillar 4 of the PyAgent spec-driven architecture for orchestrating multi-agent systems** — pattern-aware OpenTelemetry tracing. Track costs, record interactions, and debug with replay.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](../../LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

> **Architecture Pillar: 📊 Observability**
> The event backbone of the Observability pillar — a pub/sub `TraceEventBus` that captures every LLM call, token count, latency, and cost, then routes them to Console, JSONL, OpenTelemetry, or Langfuse exporters.
> Part of the full stack: install `pyagent-all` for all pillars.

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
print(f"Tokens: {tracker.total_tokens}")  # 3950

# Breakdowns
print(tracker.by_pattern())  # {"pipeline": 0.00619, "supervisor": 0.01278}
print(tracker.by_agent())  # {"extractor": 0.00019, "analyst": 0.00600, ...}
print(tracker.by_model())  # {"gpt-4o-mini": 0.00019, "gpt-4o": 0.00600, ...}

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

## TraceEventBus — Portal-Agnostic Event Pub/Sub

The `TraceEventBus` is the central hub for all trace events in the PyAgent ecosystem. It decouples event producers (agents, patterns, providers, compression) from consumers (exporters, Studio, custom handlers) using a pub/sub model.

```python
from pyagent_trace.events import TraceEvent, TraceEventBus

bus = TraceEventBus()

# Subscribe to ALL events
bus.subscribe(lambda event: print(f"[{event.event_type}] {event.data}"))

# Subscribe to specific event types only
bus.subscribe_filter(
    {"llm_call", "error", "cost"},
    lambda event: alert_on_failure(event),
)

# Emit events (typically done by agents, patterns, or providers)
bus.emit(
    TraceEvent(
        event_type="agent_start",
        data={"agent": "analyst", "input_tokens": 500},
    )
)

# Async emit for non-blocking producers
await bus.emit_async(
    TraceEvent(
        event_type="llm_call",
        data={"model": "gpt-4o", "tokens": 1200, "cost_usd": 0.006},
    )
)
```

### TraceEvent Structure

Every event flowing through the bus is a `TraceEvent` with:

| Field | Type | Description |
|-------|------|-------------|
| `event_type` | `str` | Category: `agent_start`, `agent_end`, `pattern_start`, `pattern_end`, `llm_call`, `cost`, `compression`, `error` |
| `data` | `dict` | Event-specific payload (agent name, tokens, cost, model, etc.) |
| `timestamp` | `float` | Unix timestamp of when the event was created |
| `trace_id` | `str` | Correlation ID linking related events in a single workflow execution |
| `parent_id` | `str \| None` | Parent event ID for hierarchical span nesting |

### Event Type Reference

| Event Type | Producer | Key Data Fields |
|------------|----------|----------------|
| `pattern_start` | Pattern | `pattern_type`, `input` |
| `pattern_end` | Pattern | `pattern_type`, `output`, `duration_ms`, `token_estimate` |
| `agent_start` | Agent | `agent_name`, `input` |
| `agent_end` | Agent | `agent_name`, `output`, `duration_ms` |
| `llm_call` | Agent/Provider | `model`, `input_tokens`, `output_tokens`, `cost_usd`, `latency_ms` |
| `cost` | CostTracker | `pattern`, `agent`, `model`, `cost_usd`, `tokens` |
| `compression` | CompressMiddleware | `agent`, `original_tokens`, `compressed_tokens`, `savings_pct` |
| `error` | Any | `source`, `error_type`, `message`, `traceback` |

## Built-in Exporters

PyAgent ships four exporters that plug into the `TraceEventBus`:

### ConsoleExporter — Development Debugging

Prints formatted trace events to stdout. Zero configuration.

```python
from pyagent_trace.exporters.console import ConsoleExporter

bus.subscribe(ConsoleExporter().export_event)
# Output: [2025-01-15T10:30:00] agent_start | analyst | input_tokens=500
```

### JsonlExporter — Persistent Trace Files

Appends events as newline-delimited JSON for offline analysis and replay.

```python
from pyagent_trace.exporters.jsonl import JsonlExporter

exporter = JsonlExporter("traces/run_001.jsonl")
bus.subscribe(exporter.export_event)

# After workflow completes
exporter.flush()
exporter.shutdown()
```

### OTelExporter — OpenTelemetry Backend Integration

Maps PyAgent trace events to OpenTelemetry spans. Requires `opentelemetry-api` + `opentelemetry-sdk`.

```python
from pyagent_trace.exporters.otel import OTelExporter

# Sends spans to any OTel-compatible backend (Jaeger, Grafana Tempo, Datadog, Honeycomb)
otel = OTelExporter(service_name="my-agent-system")
bus.subscribe(otel.export_event)
```

**Span mapping:**
- `pattern_start`/`pattern_end` → parent span named `pyagent.pattern.<type>`
- `agent_start`/`agent_end` → child span named `pyagent.agent.<name>`
- `llm_call` → child span with model, token, and cost attributes
- Error events set `StatusCode.ERROR` on the corresponding span

### LangfuseExporter — Langfuse Observability Platform

Maps PyAgent events to Langfuse traces, generations, and spans. Uses `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, and `LANGFUSE_HOST` environment variables.

```python
from pyagent_trace.exporters.langfuse import LangfuseExporter

langfuse = LangfuseExporter()  # reads from env vars
bus.subscribe(langfuse.export_event)

# Langfuse mapping:
# pattern_start → new Langfuse trace
# agent_start   → span within trace
# llm_call      → generation with model, tokens, cost
# pattern_end   → trace completion
```

### Multi-Backend Fan-Out

Subscribe multiple exporters to the same bus for simultaneous export:

```python
from pyagent_trace.events import TraceEventBus
from pyagent_trace.exporters.console import ConsoleExporter
from pyagent_trace.exporters.jsonl import JsonlExporter
from pyagent_trace.exporters.langfuse import LangfuseExporter

bus = TraceEventBus()

# All three receive every event
bus.subscribe(ConsoleExporter().export_event)  # dev debugging
bus.subscribe(JsonlExporter("traces/run.jsonl").export_event)  # persistent log
bus.subscribe(LangfuseExporter().export_event)  # production dashboard
```

## Custom Exporters

Implement the `TraceExporter` protocol to send events to any backend:

```python
from pyagent_trace.exporters.base import TraceExporter
from pyagent_trace.events import TraceEvent


class SlackAlertExporter(TraceExporter):
    """Send error events to a Slack channel."""

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def export_event(self, event: TraceEvent) -> None:
        if event.event_type == "error":
            # POST to Slack webhook
            requests.post(
                self.webhook_url,
                json={
                    "text": f":warning: Agent error: {event.data.get('message')}",
                },
            )

    def flush(self) -> None:
        pass  # No buffering

    def shutdown(self) -> None:
        pass  # No cleanup needed


# Wire it up
bus.subscribe(SlackAlertExporter("https://hooks.slack.com/...").export_event)
```

## Wiring Producers — Connecting CostTracker & Recorder to the Bus

Both `CostTracker` and `Recorder` accept an optional `event_bus` parameter. When provided, they automatically emit trace events for every cost record and LLM call:

```python
from pyagent_trace.events import TraceEventBus
from pyagent_trace.cost import CostTracker
from pyagent_trace.recorder import Recorder

bus = TraceEventBus()

# CostTracker emits "cost" events on every .record() call
tracker = CostTracker(event_bus=bus)
tracker.record("pipeline", "analyst", "gpt-4o", 800, 400, 0.006)
# → bus receives: TraceEvent(event_type="cost", data={...})

# Recorder emits "pattern_start", "llm_call", "pattern_end" events
recorder = Recorder(event_bus=bus)
recorder.start("debate")
recorder.record_llm_call("bull", messages, response)
recorder.end(final_output)
# → bus receives three events in sequence
```

## Integration with Other Packages

### With pyagent-patterns

Use `traced_pattern` and `traced_agent` decorators, or wire `CostTracker` + `Recorder` with the event bus to capture all pattern and agent activity.

### With pyagent-providers

Providers can emit `llm_call` events through the bus to track model usage, latency, input/output tokens, and cost per call. This enables per-provider cost attribution in Studio.

### With pyagent-compress

When `CompressMiddleware` is wired with a `TraceEventBus`, it emits `compression` events containing `original_tokens`, `compressed_tokens`, and `savings_pct` for every compressed agent output. This enables compression savings tracking in Studio.

### With pyagent-context

Context operations (ledger writes, memory tier transitions, retrieval scores) can be tracked via trace events, providing visibility into how context flows between agents and how memory is consumed.

### With pyagent-studio

Studio subscribes to the `TraceEventBus` to power:
- **Trace Viewer** — live SSE stream of trace events + historical JSONL browsing
- **Cost Dashboard** — real-time cost breakdown by pattern, agent, and model
- **Governance** — compliance monitoring based on trace data

## Other packages in this pillar

- `pyagent-studio` — web dashboard, CLI, trace explorer, governance

## Full stack

Install all pillars at once: `pip install pyagent-all`

→ [pyagent.org](https://pyagent.org) for full documentation.

## Full Documentation

See [pyagent.org](https://pyagent.org) for full API reference and integration guides.

<!-- pyagent-ecosystem-footer:start -->

## The PyAgent ecosystem

PyAgent is a spec-driven architecture for orchestrating multi-agent systems. Each package is independent — install
only what you need, or get everything with [`pip install pyagent-all`](https://pyagent.org/getting-started/).

| Package | What it gives you |
|---------|-------------------|
| `pyagent-blueprint` | [Declarative multi-agent blueprints](https://pyagent.org/guides/blueprint/) — compile, validate, and diff agent systems from YAML |
| `pyagent-patterns` | [Reusable multi-agent design patterns](https://pyagent.org/packages/patterns/) — Supervisor, Pipeline, ReAct, and 15 more |
| `pyagent-router` | [Difficulty-aware model routing](https://pyagent.org/guides/router/) — cost-efficient model selection per task |
| `pyagent-compress` | [Token-efficient agent compression](https://pyagent.org/guides/compression/) — inter-agent token budgets |
| `pyagent-providers` | [Multi-provider orchestration](https://pyagent.org/guides/providers/) — fallback chains and capability negotiation |
| `pyagent-context` | [Stateful agent memory](https://pyagent.org/guides/context/) — trust-aware, three-tier context ledger |
| `pyagent-trace` | [Multi-agent observability & tracing](https://pyagent.org/guides/tracing/) — pattern-aware OpenTelemetry spans |
| `pyagent-studio` | [Agent control plane dashboard](https://pyagent.org/guides/studio/) — live traces, cost, and governance |

**Learn more:**
[Design patterns](https://pyagent.org/packages/patterns/) ·
[Cookbook](https://pyagent.org/cookbook/) ·
[Get started](https://pyagent.org/getting-started/)

<!-- pyagent-ecosystem-footer:end -->
