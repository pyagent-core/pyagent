# pyagent-router

**Difficulty-aware routing and model selection** for multi-agent LLM workflows. Route easy tasks to cheap models, hard tasks to expensive ones — automatically.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](../../LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

## Install

```bash
pip install pyagent-router
```

Depends on: `pyagent-patterns`.

## Why Routing?

Without routing, every agent call uses the same model regardless of task complexity. A simple classification step costs the same as a deep reasoning step. `pyagent-router` scores task difficulty 1–10 and picks the cheapest model whose capability range covers it.

**Typical savings: 40–60%** for workloads where 70%+ of queries are routine.

**Supported models out of the box:** `gpt-4.1-nano`, `gpt-4o-mini`, `gpt-4.1-mini`, `gpt-4o`, `gpt-4.1`, `claude-sonnet-4`, `claude-haiku-3.5`, `gemini-2.5-flash`, `gemini-2.5-pro`, `o3-mini`, `o3`.

---

## Components

- **ModelSelector** — Score a task and return the cheapest viable model
- **DifficultyScorer** — Score task difficulty 1–10 with extensible signals
- **CostEstimator** — Estimate and compare costs across all models
- **RouterMiddleware** — Wrap agents so every call auto-routes to the right model

---

## ModelSelector — pick the right model automatically

```python
from pyagent_router import ModelSelector
from pyagent_router.selector import Capability

selector = ModelSelector()

# Basic selection
result = selector.select("What is the capital of France?")
print(result.model)                       # "gpt-4.1-nano"
print(result.reason)                      # "Difficulty 1/10 (easy) → gpt-4.1-nano (cheapest at $0.000001)"
print(result.alternatives)               # ["gpt-4o-mini", "gpt-4.1-mini"]
print(result.cost_estimate.total_cost)   # 0.0000012

# With capability filter
result = selector.select(
    "Prove that the halting problem is undecidable",
    required_capability=Capability.REASONING,
)
print(result.model)    # "o3-mini"

# Build a dynamic LLM factory — right model for each task automatically
def make_llm_for_task(task: str) -> object:
    selection = selector.select(task)
    model = selection.model
    print(f"→ {model} (difficulty {selection.difficulty.score}/10, ~${selection.cost_estimate.total_cost:.6f})")
    if "claude" in model:
        return AnthropicLLM(model)
    elif "gemini" in model:
        return GeminiLLM(model)
    else:
        return OpenAILLM(model)

llm = make_llm_for_task("What is 2+2?")                                   # → gpt-4.1-nano
llm = make_llm_for_task("Design a distributed rate limiter for 10M RPS")  # → o3-mini
```

---

## RouterMiddleware — wrap agents with automatic routing

```python
from pyagent_router import RouterMiddleware
from pyagent_router.selector import Capability

# Registry of all available models
model_registry = {
    "gpt-4.1-nano":     OpenAILLM("gpt-4.1-nano"),
    "gpt-4o-mini":      OpenAILLM("gpt-4o-mini"),
    "gpt-4o":           OpenAILLM("gpt-4o"),
    "claude-haiku-3.5": AnthropicLLM("claude-haiku-3-5-20241022"),
    "claude-sonnet-4":  AnthropicLLM("claude-sonnet-4-20250514"),
    "gemini-2.5-flash": GeminiLLM("gemini-2.5-flash"),
    "o3-mini":          OpenAILLM("o3-mini"),
}

middleware = RouterMiddleware(
    model_registry=model_registry,
    required_capability=Capability.CODE,   # optional: only consider code-capable models
)

# Wrap individual agents — every call auto-selects the cheapest appropriate model
agent = Agent("coder", OpenAILLM("gpt-4o"), system_prompt="Write Python code.")
routed_agent = middleware.wrap(agent)

result = await routed_agent.run([Message.user("Write a hello world function")])
print(result.metadata["routed_model"])    # "gpt-4.1-nano"
print(result.metadata["difficulty"])      # 1
print(result.metadata["estimated_cost"])  # 0.000001
print(result.metadata["reason"])          # "Difficulty 1/10 → gpt-4.1-nano ..."

# Wrap all agents in a pattern at once
from pyagent_patterns.orchestration import Pipeline
pipeline = Pipeline(stages=[
    Agent("planner",  OpenAILLM("gpt-4o"),     system_prompt="Plan the approach."),
    Agent("executor", OpenAILLM("gpt-4o-mini"), system_prompt="Execute the plan."),
])
pipeline._stages = middleware.wrap_all(pipeline._stages)
```

---

## DifficultyScorer — score tasks directly

```python
from pyagent_router import DifficultyScorer

scorer = DifficultyScorer()

easy = scorer.score("What does HTTP 404 mean?")
print(easy.score, easy.category, easy.is_easy)    # 1, "easy", True
print(easy.signals)                                # {"length": 0.02, "keywords": 0.0, ...}

hard = scorer.score(
    "Design a Byzantine fault-tolerant consensus algorithm for a financial system "
    "that must process 1M transactions per second with sub-100ms finality"
)
print(hard.score, hard.category, hard.is_hard)    # 9, "hard", True

# Add custom signals for domain-specific difficulty
def has_regulatory_requirement(task: str) -> float:
    keywords = ["HIPAA", "GDPR", "SOC 2", "PCI DSS", "compliance", "audit"]
    return 1.0 if any(k.lower() in task.lower() for k in keywords) else 0.0

custom_scorer = DifficultyScorer(custom_signals={"regulatory": has_regulatory_requirement})
result = custom_scorer.score("Build a HIPAA-compliant patient data API")
print(result.score)   # boosted by regulatory signal
```

---

## CostEstimator — compare costs across models

```python
from pyagent_router import CostEstimator

estimator = CostEstimator()

# Compare all models for a task
task = "Explain the CAP theorem with three concrete examples"
estimates = estimator.compare(task)
for est in estimates[:5]:
    print(f"{est.model:25s}  ${est.total_cost:.7f}  ({est.input_tokens} in, {est.output_tokens} out)")
# gpt-4.1-nano              $0.0000011  (45 in, 22 out)
# gpt-4o-mini               $0.0000034  (45 in, 22 out)
# gemini-2.5-flash          $0.0000034  (45 in, 22 out)
# gpt-4.1-mini              $0.0000090  (45 in, 22 out)
# claude-haiku-3.5          $0.0000180  (45 in, 22 out)

# Estimate a specific model
est = estimator.estimate_from_text("gpt-4o", task)
print(f"gpt-4o: ${est.total_cost:.6f} ({est.input_tokens} tokens)")

# Add custom model pricing
from pyagent_router.estimator import ModelPricing
custom_pricing = {**estimator._pricing, "my-custom-model": ModelPricing(0.50, 2.00)}
custom_estimator = CostEstimator(pricing=custom_pricing)
```

---

## Full Documentation

See [pyagent.dev](https://pyagent.dev) for full API reference and integration guides.
