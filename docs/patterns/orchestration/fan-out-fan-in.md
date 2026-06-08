# Fan-Out / Fan-In Pattern

Broadcast task to N agents in parallel, then aggregate results.

## Sequence Diagram

```mermaid
sequenceDiagram
    participant U as User
    participant O as Orchestrator
    participant F as Fundamentals
    participant T as Technicals
    participant S as Sentiment
    participant A as Aggregator

    U->>O: "Analyze AAPL"
    par Parallel Execution
        O->>F: Analyze fundamentals
        O->>T: Analyze technicals
        O->>S: Analyze sentiment
    end
    F-->>A: "P/E ratio: 28, Revenue: $94B"
    T-->>A: "RSI: 65, MACD: bullish"
    S-->>A: "85% positive sentiment"
    A-->>U: "Combined: Strong BUY"
```

## Code Example

```python
import asyncio
from pyagent_patterns.base import Agent, MockLLM
from pyagent_patterns.orchestration import FanOutFanIn

fanout = FanOutFanIn(
    agents=[
        Agent("fundamentals", MockLLM(responses=["P/E: 28, strong revenue growth"])),
        Agent("technicals", MockLLM(responses=["RSI oversold, MACD bullish crossover"])),
        Agent("sentiment", MockLLM(responses=["85% positive social sentiment"])),
    ],
    aggregator=Agent("aggregator", MockLLM(responses=["Combined analysis: Strong BUY signal"])),
)

result = asyncio.run(fanout.run("Analyze AAPL stock"))
print(result.output)
print(f"Agents used: {result.metadata['parallel_agents']}")
```

## When to Use

- ✅ **Use when:** Multiple independent analyses can run simultaneously
- ✅ **Use when:** Wall-clock latency matters (parallel = fast)
- ❌ **Avoid when:** Analyses depend on each other (use Pipeline)

## Cost-Effectiveness

| Metric | Value |
|--------|-------|
| LLM calls | N + 1 (agents + aggregator) |
| Latency | max(agent latencies) + aggregator |
| Cost | (N + 1) × single call cost |
| Quality gain | +20% (diverse perspectives) |
