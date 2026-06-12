# pyagent-all

**PyAgent: A Production Stack for Multi-Agent LLM Systems** — one command installs all four architecture pillars.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](../../LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

```bash
pip install pyagent-all
```

---

## Four Architecture Pillars

PyAgent is organised around four pillars that mirror the lifecycle of a production multi-agent system. Install them all with `pyagent-all`, or pick only the pillars you need.

---

### 📋 Pillar 1 — Blueprint

> **Declare your entire agent system in a single YAML file.**

| Package | Role | Standalone install |
|---------|------|--------------------|
| **pyagent-blueprint** | YAML spec → Pydantic validation → `RuntimeGraph`. Validate, compile, test, diff, render, and generate from the CLI. | `pip install pyagent-blueprint` |

```yaml
# customer-support.yaml
api_version: pyagent/v1
metadata: { name: customer-support, version: "1.0.0" }
providers:
  fast:   { provider: anthropic, model: claude-haiku-3-5-20241022 }
  expert: { provider: anthropic, model: claude-sonnet-4-20250514  }
agents:
  classifier: { provider: fast,   prompt: "Classify into billing, technical, general." }
  specialist: { provider: expert, prompt: "Handle the request professionally." }
workflows:
  main:
    pattern: supervisor
    agents: { classifier: classifier, routes: { billing: specialist } }
```

```bash
blueprint validate customer-support.yaml   # static analysis
blueprint test     customer-support.yaml   # contract conformance
blueprint diff     v1.yaml v2.yaml         # semantic diff
```

---

### ⚡ Pillar 2 — Execution

> **Run 18 orchestration patterns against real providers, with model routing and compression.**

| Package | Role | Standalone install |
|---------|------|--------------------|
| **pyagent-patterns** | 18 named patterns: Pipeline, Supervisor, Fan-Out, Debate, Swarm, ReAct and more | `pip install pyagent-patterns` |
| **pyagent-providers** | Multi-provider registry, routing strategies, fallback chains, capability negotiation | `pip install pyagent-providers` |
| **pyagent-router** | Difficulty scoring (1–10), cost estimation, model selection middleware | `pip install pyagent-router` |
| **pyagent-compress** | Inter-agent message compression, agent pruning, token budget enforcement | `pip install pyagent-compress` |

```python
import asyncio
from pyagent_patterns.orchestration import Pipeline
from pyagent_patterns.base import Agent
from pyagent_providers import ProviderRegistry, AnthropicLLM
from pyagent_router.middleware import RouterMiddleware

registry = ProviderRegistry()
registry.register("anthropic", AnthropicLLM)

model_registry = {
    "claude-haiku":  AnthropicLLM("claude-haiku-3-5-20241022"),
    "claude-sonnet": AnthropicLLM("claude-sonnet-4-20250514"),
}
router   = RouterMiddleware(model_registry=model_registry)
pipeline = Pipeline(stages=[
    router.wrap(Agent("extractor",  AnthropicLLM("claude-sonnet-4-20250514"))),
    router.wrap(Agent("summarizer", AnthropicLLM("claude-sonnet-4-20250514"))),
])
result = asyncio.run(pipeline.run("Summarise this quarterly report..."))
```

---

### 🧠 Pillar 3 — Context & Memory

> **Give agents structured, trust-aware memory that persists across turns.**

| Package | Role | Standalone install |
|---------|------|--------------------|
| **pyagent-context** | Three-tier memory (working / session / semantic), trust levels, sensitivity classification, compression, PII redaction | `pip install pyagent-context` |

```python
from pyagent_context import ContextLedger, ContextItem, TrustLevel, Sensitivity

ledger = ContextLedger()
ledger.append(ContextItem(
    content="Customer ID: C-10482, account since 2022",
    source="database",
    trust=TrustLevel.VERIFIED,
    sensitivity=Sensitivity.INTERNAL,
))

# Wire to all agents in a compiled graph
graph.wire_context(ledger)
```

---

### 📊 Pillar 4 — Observability

> **Trace every LLM call, track costs, and govern from a web dashboard.**

| Package | Role | Standalone install |
|---------|------|--------------------|
| **pyagent-trace** | `TraceEventBus` pub/sub, OTel spans, Langfuse export, cost tracking, record/replay | `pip install pyagent-trace` |
| **pyagent-studio** | `kubectl`-style CLI + FastAPI web dashboard: simulate, diff, trace explorer, governance, provider health | `pip install pyagent-studio` |

```python
from pyagent_trace.events import TraceEventBus

bus = TraceEventBus()
graph.wire_trace(bus)   # attach to all agents in the compiled graph
```

```bash
pyagent apply     customer-support.yaml          # load and validate
pyagent simulate  customer-support.yaml main "I need a refund"
pyagent dashboard --blueprint customer-support.yaml
```

---

## Full Stack Example

```python
import asyncio
from pyagent_blueprint import load_blueprint, BlueprintCompiler
from pyagent_providers import ProviderRegistry, AnthropicLLM
from pyagent_trace.events import TraceEventBus
from pyagent_context import ContextLedger, ContextItem, TrustLevel

# Pillar 1 — Blueprint
spec  = load_blueprint("customer-support.yaml")

# Pillar 2 — Execution
registry = ProviderRegistry()
registry.register("anthropic", AnthropicLLM)
graph = BlueprintCompiler(provider_registry=registry).compile(spec)

# Pillar 3 — Context & Memory
ledger = ContextLedger()
ledger.append(ContextItem("Customer tier: premium", source="crm", trust=TrustLevel.VERIFIED))
graph.wire_context(ledger)

# Pillar 4 — Observability
bus = TraceEventBus()
graph.wire_trace(bus)

# Run
result = asyncio.run(graph.run("main", "I was charged twice this month"))
print(result.output)
```

---

## What's Included

```
pyagent-all
├── 📋 Blueprint
│   └── pyagent-blueprint     YAML spec → RuntimeGraph
├── ⚡ Execution
│   ├── pyagent-patterns      18 orchestration patterns
│   ├── pyagent-providers     multi-provider registry + routing
│   ├── pyagent-router        difficulty-aware model selection
│   └── pyagent-compress      inter-agent compression + budgets
├── 🧠 Context & Memory
│   └── pyagent-context       three-tier memory + trust + redaction
└── 📊 Observability
    ├── pyagent-trace          TraceEventBus + OTel + cost tracking
    └── pyagent-studio         CLI + web dashboard + governance
```

---

→ Full documentation at [pyagent.org](https://pyagent.org)
