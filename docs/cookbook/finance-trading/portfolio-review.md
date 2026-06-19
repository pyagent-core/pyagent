---
description: "How to build a multi-agent portfolio review workflow in Python with PyAgent — specialist analysts plus an evaluator-optimizer memo."
tags:
  - Finance & Trading
  - Supervisor
  - Evaluator-Optimizer
  - Anthropic
  - pyagent-patterns
---

# How to Build a Multi-Agent Portfolio Review Workflow in Python

A supervisor routes each holding to a specialist analyst (equities, fixed-income, risk), then an
evaluator-optimizer loop tightens the final investment memo until it meets a quality bar.

**Patterns used:** [Supervisor](../../packages/patterns/orchestration/supervisor.md) ·
[Evaluator-Optimizer](../../packages/patterns/resolution/evaluator-optimizer.md)

```bash
pip install pyagent-patterns pyagent-providers
```

```python
import asyncio
from pyagent_patterns.base import Agent
from pyagent_patterns.orchestration import Supervisor
from pyagent_patterns.resolution import EvaluatorOptimizer
from pyagent_providers import AnthropicLLM

fast, strong = AnthropicLLM("claude-haiku-3-5-20241022"), AnthropicLLM("claude-sonnet-4-20250514")

desk = Supervisor(
    classifier=Agent("router", fast,
        system_prompt="Classify the holding into one of: equity, fixed_income, risk. Reply with only the label."),
    routes={
        "equity":       Agent("equities", strong, system_prompt="Analyse the equity position; cite valuation multiples."),
        "fixed_income": Agent("rates", strong, system_prompt="Analyse the bond position; cite duration and credit risk."),
        "risk":         Agent("risk", strong, system_prompt="Assess portfolio-level risk and concentration."),
    },
    default_route="risk",
)

memo = EvaluatorOptimizer(
    optimizer=Agent("writer", strong, system_prompt="Write a concise investment memo from the analysis."),
    evaluator=Agent("reviewer", strong, system_prompt="Score the memo 0-10 for clarity and rigor; demand fixes below 8."),
    threshold=8, max_rounds=3,
)

async def main():
    analysis = await desk.run("AAPL — 12% of the book, up 30% YTD")
    result = await memo.run(analysis.output)
    print(result.output)
    print(f"Converged in {result.metadata['rounds']} rounds")

asyncio.run(main())
```

**Expected output:** a tightened investment memo plus the number of evaluator rounds it took to clear the
quality threshold.

## Related examples

- [Research Assistant](../research-analysis/research-assistant.md) — parallel gathering + debate
- [SQL Analytics Assistant](../data-analytics/sql-analyst.md) — tool-using analyst agent

