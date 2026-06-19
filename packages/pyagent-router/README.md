# pyagent-router

**Pillar 2 of the PyAgent production stack for multi-agent LLM systems** — difficulty-aware routing and model selection. Route easy tasks to cheap models, hard tasks to capable ones.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](../../LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

> **Architecture Pillar: ⚡ Execution**
> Routes each task to the cheapest model that can handle it — scoring difficulty 1–10 and selecting from a model registry — so the Execution pillar spends money proportionally to task complexity.
> Part of the full stack: install `pyagent-all` for all pillars.

## Install

```bash
pip install pyagent-router
```

Depends on: `pyagent-patterns`.

## Why Routing?

Most LLM workloads are a mix of easy and hard tasks. Sending everything to `gpt-4o` wastes money on trivial queries. Routing to `gpt-4.1-nano` for simple tasks and `o3-mini` for complex ones typically saves **40–60%** without quality degradation.

## Supported Models

| Model | Difficulty Range | Capabilities | Input $/1M | Output $/1M |
|-------|-----------------|-------------|-----------|------------|
| `gpt-4.1-nano` | 1–3 | General | $0.10 | $0.40 |
| `gpt-4o-mini` | 1–5 | General, Code | $0.15 | $0.60 |
| `gpt-4.1-mini` | 1–6 | General, Code | $0.40 | $1.60 |
| `gpt-4o` | 1–8 | General, Code, Vision | $2.50 | $10.00 |
| `gpt-4.1` | 1–9 | General, Code, Vision | $2.00 | $8.00 |
| `claude-haiku-3.5` | 1–5 | General, Code | $0.80 | $4.00 |
| `claude-sonnet-4` | 1–9 | General, Code, Vision | $3.00 | $15.00 |
| `gemini-2.5-flash` | 1–6 | General, Code | $0.15 | $0.60 |
| `gemini-2.5-pro` | 1–9 | General, Code, Reasoning | $1.25 | $10.00 |
| `o3-mini` | 5–10 | Reasoning, Code, Math | $1.10 | $4.40 |
| `o3` | 7–10 | Reasoning, Code, Math | $10.00 | $40.00 |

## ModelSelector — Pick the Right Model Automatically

```python
from pyagent_router import ModelSelector
from pyagent_router.selector import Capability

selector = ModelSelector()

# Basic selection — cheapest model that covers the difficulty
result = selector.select("What is the capital of France?")
print(result.model)                    # "gpt-4.1-nano"
print(result.reason)                   # "Difficulty 1/10 (easy) → gpt-4.1-nano (cheapest at $0.000001)"
print(result.alternatives)             # ["gpt-4o-mini", "gpt-4.1-mini"]
print(result.cost_estimate.total_cost) # 0.0000012

# With capability filter — only consider models with REASONING capability
result = selector.select(
    "Prove that the halting problem is undecidable",
    required_capability=Capability.REASONING,
)
print(result.model)  # "o3-mini"

# Build an automatic LLM factory
def make_llm_for_task(task: str):
    selection = selector.select(task)
    print(f"→ {selection.model} (difficulty {selection.difficulty.score}/10, "
          f"~${selection.cost_estimate.total_cost:.6f})")
    return selection.model

make_llm_for_task("What is 2+2?")                                   # → gpt-4.1-nano
make_llm_for_task("Design a distributed rate limiter for 10M RPS")   # → o3-mini
```

## RouterMiddleware — Wrap Agents with Automatic Routing

```python
from pyagent_router import RouterMiddleware

# Registry of all available models (adapt to your LLM wrappers)
model_registry = {
    "gpt-4.1-nano": your_openai_llm("gpt-4.1-nano"),
    "gpt-4o-mini": your_openai_llm("gpt-4o-mini"),
    "gpt-4o": your_openai_llm("gpt-4o"),
    "o3-mini": your_openai_llm("o3-mini"),
}

middleware = RouterMiddleware(model_registry=model_registry)

# Wrap individual agents — routing happens per-call
from pyagent_patterns.base import Agent
agent = Agent("coder", your_openai_llm("gpt-4o"), system_prompt="Write Python code.")
routed_agent = middleware.wrap(agent)

# Easy task → gpt-4.1-nano; hard task → o3-mini
result = await routed_agent.run([Message.user("Write hello world")])
print(result.metadata["routed_model"])   # "gpt-4.1-nano"
print(result.metadata["difficulty"])     # 1
print(result.metadata["estimated_cost"]) # 0.000001

# Wrap all agents in a pattern at once
from pyagent_patterns.orchestration import Pipeline
pipeline = Pipeline(stages=[
    Agent("planner", llm, system_prompt="Plan."),
    Agent("executor", llm, system_prompt="Execute."),
])
pipeline._stages = middleware.wrap_all(pipeline._stages)
```

## DifficultyScorer — Score Tasks Directly

```python
from pyagent_router import DifficultyScorer

scorer = DifficultyScorer()

easy = scorer.score("What does HTTP 404 mean?")
print(easy.score, easy.category, easy.is_easy)  # 1, "easy", True
print(easy.signals)  # {"length": 0.02, "keywords": 0.0, ...}

hard = scorer.score(
    "Design a Byzantine fault-tolerant consensus algorithm for a financial system "
    "that must process 1M TPS with sub-100ms finality"
)
print(hard.score, hard.category, hard.is_hard)  # 9, "hard", True

# Add custom signals for domain-specific difficulty
def has_regulatory_requirement(task: str) -> float:
    keywords = ["HIPAA", "GDPR", "SOC 2", "PCI DSS", "compliance", "audit"]
    return 1.0 if any(k.lower() in task.lower() for k in keywords) else 0.0

custom_scorer = DifficultyScorer(custom_signals={"regulatory": has_regulatory_requirement})
result = custom_scorer.score("Build a HIPAA-compliant patient data API")
print(result.score)  # boosted by regulatory signal
```

## CostEstimator — Compare Costs Across Models

```python
from pyagent_router import CostEstimator

estimator = CostEstimator()

# Compare all models for a task
task = "Explain the CAP theorem with three concrete examples"
estimates = estimator.compare(task)
for est in estimates[:5]:
    print(f"{est.model:25s} ${est.total_cost:.7f} ({est.input_tokens} in, {est.output_tokens} out)")
# gpt-4.1-nano              $0.0000011 (45 in, 22 out)
# gpt-4o-mini               $0.0000034 (45 in, 22 out)
# gemini-2.5-flash           $0.0000034 (45 in, 22 out)

# Estimate a specific model
est = estimator.estimate_from_text("gpt-4o", task)
print(f"gpt-4o: ${est.total_cost:.6f} ({est.input_tokens} tokens)")

# Add custom model pricing
from pyagent_router.estimator import ModelPricing
custom_pricing = {**estimator._pricing, "my-model": ModelPricing(0.50, 2.00)}
custom_estimator = CostEstimator(pricing=custom_pricing)
```

## Integration with pyagent-patterns

```python
import asyncio
from pyagent_patterns.base import Agent, MockLLM
from pyagent_patterns.orchestration import Pipeline
from pyagent_router import ModelSelector, CostEstimator

selector = ModelSelector()
estimator = CostEstimator()

# Before running, estimate costs
task = "Analyse market trends in autonomous vehicles"
selection = selector.select(task)
est = estimator.estimate_from_text(selection.model, task)
print(f"Will use {selection.model} (~${est.total_cost:.6f})")

# Typical savings: 40-60% vs always using the most expensive model
```

## Other packages in this pillar

- `pyagent-patterns` — 18 orchestration patterns
- `pyagent-providers` — multi-provider registry
- `pyagent-compress` — inter-agent compression and token budgets

## Full stack

Install all pillars at once: `pip install pyagent-all`

→ [pyagent.org](https://pyagent.org) for full documentation.

## Full Documentation

See [pyagent.org](https://pyagent.org) for full API reference and integration guides.

<!-- pyagent-ecosystem-footer:start -->

## The PyAgent ecosystem

PyAgent is a production stack for multi-agent LLM systems. Each package is independent — install
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
