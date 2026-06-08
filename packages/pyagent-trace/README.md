# pyagent-trace

**Pattern-aware OpenTelemetry tracing** for multi-agent LLM systems. Track costs, record interactions, debug with replay.

## Install

```bash
pip install pyagent-trace              # Core (CostTracker, Recorder work without OTel)
pip install pyagent-trace[otel]        # With OpenTelemetry spans
```

## Components

- **CostTracker** — Accumulate costs by pattern, agent, and model (no OTel required)
- **Recorder** — Record all messages + LLM responses to JSONL for replay/debug
- **PatternSpanEmitter** — Create OTel spans for pattern executions (requires OTel)
- **traced_pattern / traced_agent** — Decorators for automatic tracing (requires OTel)
- **PyAgentAttributes** — Custom `pyagent.*` attribute constants

## Quick Example (no OTel required)

```python
from pyagent_trace import CostTracker, Recorder

tracker = CostTracker()
tracker.record("debate", "bull_agent", "gpt-4o", 500, 200, 0.003)
print(f"Total: ${tracker.total_cost:.4f}")
print(f"By model: {tracker.by_model()}")

recorder = Recorder()
recorder.start("debate")
recorder.record_llm_call("bull", messages, "Bull case: ...")
recorder.end("Final decision")
recorder.save("traces/debug.jsonl")
```
