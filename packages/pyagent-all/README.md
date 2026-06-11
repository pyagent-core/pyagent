# pyagent-all

Meta-package that installs the complete PyAgent suite. One command, everything included.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](../../LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

## Install

```bash
pip install pyagent-all
```

## What's Included

| Package | Description |
|---------|-------------|
| **pyagent-patterns** | 18 multi-agent orchestration patterns + composites + guardrails + recovery |
| **pyagent-router** | Difficulty scoring, cost estimation, model selection, routing middleware |
| **pyagent-compress** | Inter-agent message compression, agent pruning, interaction pruning, token budgets |
| **pyagent-trace** | TraceEventBus pub/sub, OpenTelemetry spans, Langfuse export, cost tracking, record/replay |
| **pyagent-providers** | Multi-provider abstraction, registry, routing strategies, fallback chains, capability negotiation, cost optimizer |
| **pyagent-context** | Structured context with trust/sensitivity metadata, three-tier memory (working/session/semantic), compression, retrieval, redaction |
| **pyagent-blueprint** | Declarative YAML specs, Pydantic validation, compilation to RuntimeGraph, contract testing, Mermaid rendering, semantic diff, CLI |
| **pyagent-studio** | CLI + web control plane for designing, simulating, debugging, and governing agent blueprints with live trace streaming |

## Quick Start

```python
import asyncio
from pyagent_patterns.base import Agent, MockLLM
from pyagent_patterns.orchestration import Pipeline
from pyagent_router import ModelSelector
from pyagent_compress import MessageCompressor, CompressMiddleware, TokenBudget
from pyagent_trace import CostTracker
from pyagent_trace.events import TraceEventBus
from pyagent_providers import ProviderRegistry, MockProvider
from pyagent_context import ContextLedger, ContextItem, TrustLevel

# Set up tracing
bus = TraceEventBus()
tracker = CostTracker(event_bus=bus)

# Set up compression with token budget
budget = TokenBudget(workflow_limit=50_000, per_agent_limit=10_000)
middleware = CompressMiddleware(
    compressor=MessageCompressor(target_ratio=0.5),
    budget=budget,
)

# Build and run a pipeline
llm = MockLLM(responses=["Key facts extracted", "Concise summary"])
pipeline = Pipeline(stages=[
    middleware.wrap(Agent("extractor", llm, system_prompt="Extract key facts.")),
    Agent("summarizer", llm, system_prompt="Write a concise summary."),
])

result = asyncio.run(pipeline.run("Process this document"))
print(result.output)         # "Concise summary"
print(budget.summary())      # Token usage per agent
print(tracker.summary())     # Cost breakdown by pattern/agent/model
```

## End-to-End Flow

The packages are designed to work together in a layered architecture:

1. **Blueprint** → Define agents, workflows, providers, contracts, observability, and context in YAML
2. **Compile** → `BlueprintCompiler` produces a `RuntimeGraph` of patterns and agents
3. **Orchestrate** → Patterns (Pipeline, Supervisor, Debate, etc.) coordinate agents
4. **Provide** → `ProviderRegistry` + `FallbackChain` handle LLM calls with resilience
5. **Trace** → `TraceEventBus` collects events from agents, patterns, providers, and compression
6. **Compress** → `CompressMiddleware` reduces inter-agent token transfer; `TokenBudget` enforces limits
7. **Remember** → `ContextLedger` with three-tier memory (working → session → semantic) persists context
8. **Observe** → Studio dashboard visualizes traces, costs, governance, and agent communication

## Documentation

See [pyagent.org](https://pyagent.org) for full docs, API reference, and cookbook.
