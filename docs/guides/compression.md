# Compression Guide

**pyagent-compress** reduces inter-agent token transfer — saving cost without losing critical signal between stages of a pipeline or fan-out.

```bash
pip install pyagent-compress
```

---

## Why Compression Saves Real Money

In a 5-agent pipeline, verbose LLM outputs compound quickly:

```
Without compression:
  Stage 1 → Stage 2:  1,200 tokens
  Stage 2 → Stage 3:  1,800 tokens (growing with context)
  Stage 3 → Stage 4:  2,100 tokens
  Total input tokens consumed by stages 2–5: ~12,000 tokens
  At GPT-4o ($5/1M input tokens): $0.060 per run

With CompressMiddleware(target_ratio=0.5):
  Total: ~6,000 tokens → $0.030 per run
  At 1,000 runs/day → saves ~$900/month
```

---

## MessageCompressor — Core Primitive

```python
from pyagent_compress import MessageCompressor

compressor = MessageCompressor(target_ratio=0.5)

verbose = """
Let me think carefully about what I've extracted from this earnings report.
The analysis shows, quite clearly I think, that Tesla's revenue for Q3 2025
increased by approximately 15% on a year-over-year basis, which is quite notable.
It is also worth mentioning that profit margins expanded to around 23%, which
represents a meaningful improvement over the prior period's figure of 19%.
Additionally, the company noted strong growth in its energy storage segment.
"""

result = compressor.compress(verbose)
print(result.compressed_text)
# "Tesla Q3 2025 revenue +15% YoY, profit margin 23% (prev 19%), energy storage strong."

print(f"{result.original_tokens} → {result.compressed_tokens} tokens ({result.savings_pct:.0%} saved)")
# 95 → 22 tokens (77% saved)
```

---

## TokenBudget — Workflow-Level Cost Control

```python
from pyagent_compress import TokenBudget

budget = TokenBudget(
    workflow_limit=30_000,   # hard ceiling for the whole workflow
    per_agent_limit=8_000,   # per-agent ceiling
)

# Record usage as agents run
budget.consume("extractor",   3_200)
budget.consume("fact_checker", 4_100)
budget.consume("risk_agent",   2_900)

print(budget.summary())
# Total: 10,200 / 30,000 (34.0%) | Remaining: 19,800
# By agent: {extractor: 3200, fact_checker: 4100, risk_agent: 2900}

# Pre-flight check before an expensive agent
if budget.remaining("writer") < 5_000:
    print("Compress inputs before calling the writer agent")

# Strict mode: raise on budget exceeded instead of silently compressing
strict = TokenBudget(workflow_limit=10_000, strict=True)
```

---

## CompressMiddleware — Automatic Pipeline Integration

Wrap agents so their outputs are compressed before passing to the next stage.

### Pipeline with automatic compression

```python
import asyncio
from pyagent_compress import CompressMiddleware, TokenBudget
from pyagent_patterns.base import Agent
from pyagent_patterns.orchestration import Pipeline
from pyagent_providers import AnthropicLLM, OpenAILLM, GeminiLLM

budget     = TokenBudget(workflow_limit=40_000, per_agent_limit=8_000)
middleware = CompressMiddleware(target_ratio=0.5, budget=budget)

pipeline = Pipeline(stages=[
    middleware.wrap(Agent(
        "extractor",
        AnthropicLLM("claude-haiku-3-5-20241022"),
        system_prompt="Extract all facts, figures, entities, and key claims from the document.",
    )),
    middleware.wrap(Agent(
        "risk_analyst",
        OpenAILLM("gpt-4o-mini"),
        system_prompt="Identify the top 5 risk factors with severity (HIGH/MEDIUM/LOW).",
    )),
    middleware.wrap(Agent(
        "opportunity_analyst",
        GeminiLLM("gemini-2.5-flash"),
        system_prompt="Identify the top 3 growth opportunities.",
    )),
    # Last stage: no compression — output goes straight to the user
    Agent(
        "writer",
        AnthropicLLM("claude-sonnet-4-20250514"),
        system_prompt="Write an executive brief. Lead with the top risk. Max 300 words.",
    ),
])

result = asyncio.run(pipeline.run(open("earnings_transcript.txt").read()))
print(result.output)
print(f"Budget used: {budget.summary()}")
print(f"Cost: ${result.cost_estimate:.4f}")
```

### Wrap all agents at once

```python
agents = [extractor, risk_analyst, opportunity_analyst]
compressed_stages = middleware.wrap_all(agents)

pipeline = Pipeline(stages=[*compressed_stages, writer_agent])
```

---

## Fan-Out with Compression

Parallel agents produce verbose analyses; compress each before the aggregator.

```python
from pyagent_compress import CompressMiddleware, TokenBudget
from pyagent_patterns.orchestration import FanOutFanIn
from pyagent_providers import GeminiLLM, AnthropicLLM

# Without compression: 3 agents × ~1500 tokens each = 4500 tokens to aggregator
# With 0.4 ratio:       3 agents × ~600 tokens each = 1800 tokens to aggregator

budget     = TokenBudget(workflow_limit=60_000, per_agent_limit=8_000)
middleware = CompressMiddleware(target_ratio=0.4, budget=budget)

fanout = FanOutFanIn(
    agents=[
        middleware.wrap(Agent("bull",    GeminiLLM("gemini-2.5-flash"),
                              system_prompt="Argue the strongest possible bullish case with data.")),
        middleware.wrap(Agent("bear",    GeminiLLM("gemini-2.5-flash"),
                              system_prompt="Argue the strongest possible bearish case with data.")),
        middleware.wrap(Agent("neutral", GeminiLLM("gemini-2.5-flash"),
                              system_prompt="Give a balanced, probability-weighted assessment.")),
    ],
    aggregator=Agent(
        "analyst",
        AnthropicLLM("claude-sonnet-4-20250514"),
        system_prompt="Synthesise all perspectives into a structured investment memo.",
    ),
)

result = asyncio.run(fanout.run("Nvidia at $3.2T market cap — invest or pass?"))
print(f"Tokens passed to aggregator: ~{budget.total_consumed} (vs ~4500 uncompressed)")
```

---

## AgentPruner — Remove Low-Contribution Agents

After running a fan-out, detect which agents added unique value and which just duplicated others.

```python
from pyagent_compress import AgentPruner

pruner = AgentPruner(min_contribution=0.3)

# Message history from a 3-agent fan-out
message_history = [
    {"agent": "bull",    "content": "Strong earnings growth and AI moat justify 45x P/E."},
    {"agent": "bear",    "content": "Strong earnings growth and AI moat justify 45x P/E."},  # near-duplicate
    {"agent": "neutral", "content": "Key swing factor: AMD custom silicon — $40B TAM shift risk."},
]

scores = pruner.score_agents(message_history, task="Nvidia investment decision")
print(scores)
# {"bull": 0.84, "bear": 0.19, "neutral": 0.91}

to_prune = pruner.should_prune(scores)
print(f"Agents to remove from future runs: {to_prune}")
# → ["bear"]

# Remove the low-value agent from your configuration
from pyagent_patterns.orchestration import FanOutFanIn
optimised_fanout = FanOutFanIn(
    agents=[bull_agent, neutral_agent],   # bear removed
    aggregator=analyst_agent,
)
```

---

## InteractionPruner — Compress Long Conversation History

Before injecting session history into an agent, remove low-relevance exchanges.

```python
from pyagent_compress import InteractionPruner
from pyagent_context.memory.session import SessionMemory

pruner = InteractionPruner(max_interactions=10, min_relevance=0.4)

session = SessionMemory(session_id="support-4421")
history = session.get_all()

print(f"Full history: {len(history)} items")
pruned = pruner.prune(
    [{"role": item.source, "content": item.content} for item in history],
    current_query="I want to upgrade my plan",
)
print(f"After pruning: {len(pruned)} interactions (relevance-filtered)")
```

---

## Compression in Blueprint YAML

Declare compression requirements declaratively:

```yaml
context:
  compress_ratio: 0.5         # auto-applied via CompressMiddleware
  working_memory_tokens: 20000
```

The BlueprintCompiler wires `CompressMiddleware` automatically when `compress_ratio` is set.

---

## OTel Tracing for Compression

Compression savings are surfaced as OTel span attributes — visible in Studio's trace explorer:

```python
from pyagent_trace import PatternSpanEmitter

emitter = PatternSpanEmitter()
span = emitter.pattern_span("pipeline", {})

# After running with middleware:
emitter.set_attribute(span, "pyagent.compress.savings_pct", 0.52)
emitter.set_attribute(span, "pyagent.compress.tokens_saved", 6_200)
span.end()
# → visible in Jaeger / Langfuse / Studio as pyagent.compress.savings_pct: 0.52
```

---

## Cost Savings Reference

| Workflow | Without Compression | With `target_ratio=0.5` | Monthly saving (1k runs/day) |
|----------|--------------------|-----------------------|------------------------------|
| 5-stage Pipeline (gpt-4o) | 25k tok → $0.125 | 13k tok → $0.065 | **$1,800** |
| 5-agent Fan-Out (gemini-2.5-pro) | 30k tok → $0.030 | 16k tok → $0.016 | **$420** |
| 3-round Debate (gpt-4o) | 18k tok → $0.090 | 10k tok → $0.050 | **$1,200** |

---

## See Also

- [Compress Package](../packages/compress.md) — full API reference
- [Context Package](../packages/context.md) — `ContextLedger.to_messages(max_tokens=)` for budget-aware injection
- [Tracing Guide](tracing.md) — `pyagent.compress.savings_pct` OTel attribute
- [Pipeline Pattern](../patterns/orchestration/pipeline.md) — see CompressMiddleware example in context
