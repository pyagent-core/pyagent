# pyagent-trace

**Pattern-aware OpenTelemetry tracing** for multi-agent LLM systems. Track costs, record interactions, and debug with replay.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](../../LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

## Install

```bash
pip install pyagent-trace              # Core (CostTracker, Recorder work without OTel)
pip install pyagent-trace[otel]        # With OpenTelemetry spans
```

Depends on: `pyagent-patterns`. OTel extras: `opentelemetry-api`, `opentelemetry-sdk`.

## Why Tracing?

Multi-agent workflows are hard to debug — a single run can involve dozens of LLM calls across multiple patterns. `pyagent-trace` adds structured OTel spans with `pyagent.*` attributes for every pattern run, agent call, routing decision, and compression event. `CostTracker` and `Recorder` work without any OTel setup for lightweight cost tracking and replay.

---

## Components

- **traced_pattern** — Decorator to auto-emit OTel spans on every `.run()` call
- **traced_agent** — Decorator to trace individual agent calls
- **CostTracker** — Accumulate and break down costs by pattern, agent, and model (no OTel required)
- **Recorder** — Record all LLM calls to JSONL for replay and debugging (no OTel required)
- **PatternSpanEmitter** — Manual OTel span control for custom patterns

---

## traced_pattern decorator — auto-trace a pattern class

```python
from pyagent_trace import traced_pattern
from pyagent_patterns.orchestration import Pipeline
from pyagent_patterns.resolution import Debate

# Decorate the class — every .run() call now emits an OTel span
@traced_pattern
class TracedPipeline(Pipeline):
    pass

# Or apply to an existing class without subclassing
TracedDebate = traced_pattern(Debate)

# Configure OTel exporter first (Jaeger, Honeycomb, Grafana Tempo, OTLP...)
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

provider = TracerProvider()
provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint="http://localhost:4317")))
trace.set_tracer_provider(provider)

# All runs now emit spans automatically
pipeline = TracedPipeline(stages=[...])
result = asyncio.run(pipeline.run("My task"))
# → OTel span: "pyagent.pattern.pipeline"
#   attributes: pyagent.pattern.type, pyagent.exec.duration_ms,
#               pyagent.exec.token_estimate, pyagent.cost.total_usd
```

---

## traced_agent — trace individual agents

```python
from pyagent_trace import traced_agent

agent = traced_agent(Agent("analyst", OpenAILLM("gpt-4o"), system_prompt="Analyse data."))
# Every agent.run() now emits a "pyagent.agent.analyst" span
```

---

## CostTracker — track costs across a workflow

```python
from pyagent_trace import CostTracker

tracker = CostTracker()

# Record costs manually or integrate with your routing middleware
tracker.record("pipeline",   "extractor",  "gpt-4o-mini",      500, 200, 0.00019)
tracker.record("pipeline",   "analyst",    "gpt-4o",           800, 400, 0.00600)
tracker.record("supervisor", "classifier", "claude-haiku-3.5", 200,  50, 0.00018)
tracker.record("supervisor", "specialist", "claude-sonnet-4", 1200, 600, 0.01260)

print(f"Total: ${tracker.total_cost:.5f}")   # $0.01897
print(f"Tokens: {tracker.total_tokens}")     # 3950

# Breakdowns
print(tracker.by_pattern())  # {"pipeline": 0.00619, "supervisor": 0.01278}
print(tracker.by_agent())    # {"extractor": 0.00019, "analyst": 0.00600, ...}
print(tracker.by_model())    # {"gpt-4o-mini": 0.00019, "gpt-4o": 0.00600, ...}

print(tracker.summary())
# {
#   "total_cost_usd": 0.01897,
#   "total_tokens": 3950,
#   "entries": 4,
#   "by_pattern": {...},
#   "by_agent": {...},
#   "by_model": {...}
# }
```

---

## Recorder — record and replay pattern executions

```python
from pyagent_trace import Recorder

recorder = Recorder()
recorder.start("debate")

# Record LLM calls as they happen (integrate in your pattern or middleware)
recorder.record_llm_call(
    agent_name="bull_debater",
    messages=[Message.user("Argue the bull case for NVDA")],
    response="Strong data center growth driven by AI training demand...",
    metadata={"round": 1, "model": "gemini-2.5-flash"},
)

recorder.end(result.output)

# Save full trace to disk
recorder.save("traces/debate_nvda_2025-11-15.jsonl")

# Load and inspect later
entries = Recorder.load("traces/debate_nvda_2025-11-15.jsonl")
for entry in recorder.llm_calls:
    print(f"[{entry.agent_name}] → {entry.response[:80]}...")
    print(f"  Metadata: {entry.metadata}")
```

---

## PatternSpanEmitter — manual span control

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

---

## Full Documentation

See [pyagent.dev](https://pyagent.dev) for full API reference and integration guides.
