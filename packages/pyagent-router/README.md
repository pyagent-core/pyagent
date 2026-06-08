# pyagent-router

**Difficulty-aware routing and model selection** for multi-agent LLM workflows. Route easy tasks to cheap models, hard tasks to expensive ones.

## Install

```bash
pip install pyagent-router
```

## Components

- **DifficultyScorer** — Score task difficulty 1-10 based on heuristics
- **CostEstimator** — Estimate LLM call costs with built-in model pricing
- **ModelSelector** — Auto-select the cheapest viable model
- **RouterMiddleware** — Inject routing into agent calls

## Quick Example

```python
from pyagent_router import ModelSelector

result = ModelSelector().select("What is 2+2?")
print(f"{result.model}: ${result.cost_estimate.total_cost:.6f}")
# gpt-4.1-nano: $0.000002 (instead of $0.003 with gpt-4o)
```

## Typical Savings: 40-60%

For workloads where 70% of queries are easy, routing to cheap models saves 40-60% vs always using the most expensive model.
