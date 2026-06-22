---
description: "Get started with PyAgent — install the packages and run your first multi-agent pattern in minutes, from a single agent to a full pipeline."
---

# Getting Started

## Installation

```bash
# Core patterns only (zero LLM deps)
pip install pyagent-patterns

# With routing
pip install pyagent-router

# With compression
pip install pyagent-compress

# With tracing (requires opentelemetry)
pip install pyagent-trace

# Everything
pip install pyagent-all
```

New to PyAgent? The four primitives — Message, Agent, Pattern, Result — are covered in
[Core Concepts](getting-started/core-concepts.md).

## Your First Pattern

```python
import asyncio
from pyagent_patterns.base import Agent, MockLLM
from pyagent_patterns.resolution import SelfReflection

llm = MockLLM(responses=[
    "def fibonacci(n): return n if n <= 1 else fibonacci(n-1) + fibonacci(n-2)",
    "Critique: naive recursion, O(2^n). Needs memoization.",
    "from functools import lru_cache\n@lru_cache\ndef fibonacci(n): return n if n <= 1 else fibonacci(n-1) + fibonacci(n-2)",
    "APPROVED — O(n) with memoization",
])

pattern = SelfReflection(agent=Agent("coder", llm), max_rounds=3)
result = asyncio.run(pattern.run("Write an efficient Fibonacci function"))
print(result.output)
print(f"Improved in {result.metadata['rounds']} rounds")
```

## Pattern Advisor

Not sure which pattern to use? Let the advisor decide:

```python
from pyagent_patterns.advisor import PatternAdvisor, Constraints, Quality

advisor = PatternAdvisor()
rec = advisor.recommend("Write and review a legal contract", Constraints(quality=Quality.HIGH))
print(f"Use: {rec.pattern} — {rec.reason}")
print(f"Estimated calls: {rec.estimated_calls}, Cost: {rec.estimated_cost_range}")
```

## Adding Hooks (Optional)

Agents support opt-in hooks for tracing, context memory, compression, and cost tracking — zero overhead when not wired:

```python
from pyagent_trace.events import TraceEventBus
from pyagent_trace import CostTracker
from pyagent_context import ContextLedger
from pyagent_compress import MessageCompressor

bus = TraceEventBus()
bus.subscribe(lambda e: print(f"[{e.event_type}] {e.agent_name}"))

agent = (
    Agent("analyst", llm, system_prompt="Analyze data.")
    .set_trace_bus(bus)                              # emit trace events
    .set_context(ContextLedger())                    # read/write context
    .set_compressor(MessageCompressor(0.5))          # compress output
    .set_cost_tracker(CostTracker(event_bus=bus))    # track costs
)

result = asyncio.run(agent.run("What are the key trends?"))
# Console prints: [agent_start] analyst → [agent_end] analyst
```

All hooks are `None` by default — existing code works identically without them.

## Next Steps

- [Pattern Selection Guide](packages/patterns/index.md) — decision tree + all 18 patterns
- [Hooks Guide](guides/hooks.md) — tracing, context, compression, and cost hooks
- [Router Guide](guides/router.md) — auto-select cheapest model
- [Compression Guide](guides/compression.md) — reduce token costs
- [Tracing Guide](guides/tracing.md) — OpenTelemetry observability
- [API & Hooks Bibliography](api/bibliography.md) — complete reference for all packages
