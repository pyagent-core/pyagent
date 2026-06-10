# Tracing Guide

**pyagent-trace** instruments every pattern execution with OpenTelemetry spans — giving you cost tracking, latency histograms, record/replay debugging, and a direct feed into Studio's trace explorer.

```bash
pip install pyagent-trace
pip install pyagent-trace[langfuse]   # production LLM observability
```

---

## How Tracing Works

Every pattern run emits a tree of OTel spans:

```
pyagent.pattern.pipeline  (root span)
├── pyagent.agent.extractor     ← one child span per agent call
├── pyagent.agent.fact_checker
└── pyagent.agent.writer
```

Each span carries structured attributes — cost, tokens, model, duration — so you can slice and aggregate in any OTel-compatible backend.

---

## Quickstart — Decorator Approach

```python
from pyagent_trace import traced_pattern, traced_agent
from pyagent_patterns.base import Agent
from pyagent_patterns.orchestration import Pipeline
from pyagent_providers import AnthropicLLM, OpenAILLM
import asyncio

@traced_pattern
class TracedPipeline(Pipeline):
    pass

pipeline = TracedPipeline(stages=[
    traced_agent(Agent("extractor", AnthropicLLM("claude-haiku-3-5-20241022"),
                       system_prompt="Extract key claims and figures.")),
    traced_agent(Agent("analyst",   OpenAILLM("gpt-4o-mini"),
                       system_prompt="Identify risk factors.")),
    traced_agent(Agent("writer",    AnthropicLLM("claude-sonnet-4-20250514"),
                       system_prompt="Write an executive brief.")),
])

result = asyncio.run(pipeline.run("Tesla Q3 2025 earnings report..."))
print(result.output)
# Spans are automatically emitted to the configured OTel backend
```

---

## Backend Setup

### Jaeger — local development

```bash
docker run -d --name jaeger \
  -p 6831:6831/udp -p 16686:16686 \
  jaegertracing/all-in-one:latest
```

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter

provider = TracerProvider()
provider.add_span_processor(
    BatchSpanProcessor(JaegerExporter(agent_host_name="localhost", agent_port=6831))
)
trace.set_tracer_provider(provider)
# Visit http://localhost:16686 → search service "pyagent"
```

### Langfuse — production LLM observability

```bash
pip install pyagent-trace[langfuse]
```

```python
from pyagent_trace.exporters.langfuse import configure_langfuse

configure_langfuse(
    public_key="pk-lf-...",
    secret_key="sk-lf-...",
    host="https://cloud.langfuse.com",
)
# Every LLM call: prompt, response, tokens, cost → Langfuse dashboard
```

### Grafana Tempo (OTLP)

```python
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace.export import BatchSpanProcessor

provider.add_span_processor(
    BatchSpanProcessor(OTLPSpanExporter(endpoint="http://tempo:4317"))
)
# Connect Grafana datasource to Tempo for trace exploration + Prometheus metrics
```

### Datadog APM

```bash
pip install pyagent-trace[datadog]
```

```python
from pyagent_trace.exporters.datadog import configure_datadog
configure_datadog(service="my-agent-service", env="production")
```

---

## PatternSpanEmitter — Manual Span Control

For patterns that need custom span attributes or error handling.

```python
from pyagent_trace import PatternSpanEmitter
from pyagent_patterns.resolution import Debate
from pyagent_providers import GeminiLLM, AnthropicLLM
from pyagent_patterns.base import Agent
import asyncio

debate = Debate(
    debaters=[Agent("bull", GeminiLLM("gemini-2.5-flash"), system_prompt="Argue the bull case."),
              Agent("bear", GeminiLLM("gemini-2.5-flash"), system_prompt="Argue the bear case.")],
    judge=Agent("judge", AnthropicLLM("claude-sonnet-4-20250514"), system_prompt="Render a verdict."),
    rounds=2,
)

emitter = PatternSpanEmitter(service_name="investment-analysis")

async def run_traced_debate():
    span = emitter.pattern_span("debate", attributes={
        "rounds": 2,
        "topic": "nvidia_investment",
        "portfolio_id": "pf-001",
    })
    try:
        result = await debate.run("Should we buy Nvidia at $3.2T market cap?")
        emitter.set_pattern_result(
            span,
            output_len=len(result.output),
            rounds=result.metadata.get("rounds", 2),
            cost_estimate=result.cost_estimate,
        )
        return result
    except Exception as exc:
        emitter.record_error(span, exc)
        raise
    finally:
        span.end()

result = asyncio.run(run_traced_debate())
```

---

## CostTracker

Track costs across a full session — aggregate by pattern, model, or agent.

```python
from pyagent_trace import CostTracker

tracker = CostTracker()

# Wire into any pattern manually, or use traced_agent for automatic recording
tracker.record("pipeline", "extractor", "claude-haiku-3-5-20241022",
               input_tokens=180, output_tokens=42, cost_usd=0.000060)
tracker.record("pipeline", "analyst",   "gpt-4o-mini",
               input_tokens=60,  output_tokens=85, cost_usd=0.000090)
tracker.record("pipeline", "writer",    "claude-sonnet-4-20250514",
               input_tokens=145, output_tokens=220, cost_usd=0.008400)

print(f"Total: ${tracker.total_cost:.4f}")

print("By pattern:", tracker.by_pattern())
# → {"pipeline": 0.008550}

print("By model:", tracker.by_model())
# → {"claude-haiku-3-5-20241022": 0.000060,
#    "gpt-4o-mini": 0.000090,
#    "claude-sonnet-4-20250514": 0.008400}

print("By agent:", tracker.by_agent())
# → {"extractor": 0.000060, "analyst": 0.000090, "writer": 0.008400}

# Budget projections
runs_per_day = 500
print(f"Daily cost at {runs_per_day} runs: ${tracker.total_cost * runs_per_day:.2f}")
print(f"Monthly: ${tracker.total_cost * runs_per_day * 30:.2f}")
```

---

## Record & Replay

Record LLM interactions to JSONL — replay them in tests and CI without hitting APIs.

```python
from pyagent_trace.recorder import Recorder

# --- Record a production run ---
recorder = Recorder()
recorder.start("pipeline")
recorder.record_llm_call(
    agent_name="extractor",
    messages=[{"role": "user", "content": "Tesla Q3 2025 report..."}],
    response="Revenue $25.2B (+8% YoY), gross margin 17.1%",
    model="claude-haiku-3-5-20241022",
    input_tokens=180, output_tokens=42, cost_usd=0.000060,
)
recorder.record_llm_call(
    agent_name="writer",
    messages=[{"role": "user", "content": "Revenue $25.2B..."}],
    response="Tesla Q3: Revenue beat consensus by 2%...",
    model="claude-sonnet-4-20250514",
    input_tokens=145, output_tokens=220, cost_usd=0.008400,
)
recorder.end("Tesla Q3: Revenue beat consensus by 2%...")
recorder.save("traces/pipeline_run_001.jsonl")
```

```python
# --- Replay in tests (zero API cost) ---
from pyagent_trace.recorder import Recorder, ReplayLLM

entries = Recorder.load("traces/pipeline_run_001.jsonl")
for entry in entries:
    print(f"[{entry.event_type}] {entry.agent_name}: {entry.response[:60]}...")

# Use ReplayLLM to re-run the pipeline deterministically
replay_extractor = ReplayLLM.from_recording("traces/pipeline_run_001.jsonl", "extractor")
replay_writer    = ReplayLLM.from_recording("traces/pipeline_run_001.jsonl", "writer")

import asyncio
from pyagent_patterns.orchestration import Pipeline
from pyagent_patterns.base import Agent

replay_pipeline = Pipeline(stages=[
    Agent("extractor", replay_extractor, system_prompt="Extract facts."),
    Agent("writer",    replay_writer,    system_prompt="Write brief."),
])
result = asyncio.run(replay_pipeline.run("Tesla Q3 2025..."))
assert "Revenue beat consensus" in result.output   # deterministic test
```

---

## Integration with pyagent-studio

Recorded `.jsonl` files load directly into Studio's visual trace explorer:

```bash
# View traces in Studio dashboard
pyagent dashboard --trace traces/pipeline_run_001.jsonl
```

Or query programmatically via TraceService:

```python
from pyagent_studio.services.trace_service import TraceService

svc = TraceService()
spans = svc.load("traces/pipeline_run_001.jsonl")

print(f"Spans: {len(spans)}")
for span in spans:
    print(f"  [{span.event_type}] {span.agent_name}: {span.duration_ms:.0f}ms")

# Analyse costs across many runs
cost_spans = svc.query(event_type="llm_call")
total_tokens = sum(s.tokens for s in cost_spans)
print(f"Total tokens across all recorded runs: {total_tokens:,}")
```

---

## Span Attribute Reference

| Attribute | Type | Description |
|-----------|------|-------------|
| `pyagent.pattern.type` | string | Pattern name: `"pipeline"`, `"debate"`, etc. |
| `pyagent.pattern.rounds` | int | Rounds executed (reflection, debate patterns) |
| `pyagent.agent.name` | string | Agent identifier |
| `pyagent.agent.model` | string | LLM model used |
| `pyagent.cost.input_tokens` | int | Prompt token count |
| `pyagent.cost.output_tokens` | int | Completion token count |
| `pyagent.cost.total_usd` | float | Estimated cost (USD) |
| `pyagent.exec.duration_ms` | float | Wall-clock time (ms) |
| `pyagent.router.difficulty` | int | Task difficulty 1–10 from pyagent-router |
| `pyagent.router.selected_model` | string | Model chosen by router |
| `pyagent.compress.savings_pct` | float | Compression savings 0–1 |
| `pyagent.early_stop` | bool | Pattern stopped before max rounds |
| `pyagent.route_key` | string | Selected route in Supervisor pattern |

---

## See Also

- [Trace Package](../packages/trace.md) — full API and backend setup reference
- [Studio Package](../packages/studio.md) — visual trace explorer, cost dashboards
- [Compression Guide](compression.md) — `pyagent.compress.savings_pct` attribute
