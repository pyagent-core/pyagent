# PyAgent

**18 reusable multi-agent orchestration patterns for LLMs** — with routing, compression, and OTel tracing.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

---

## Why PyAgent?

Existing frameworks give you raw primitives but no **named, tested, composable patterns**. PyAgent fills this gap with 18 battle-tested orchestration patterns, plus cross-cutting concerns (routing, compression, tracing) as separate installable packages.

| Feature | LangGraph | CrewAI | AutoGen | **PyAgent** |
|---------|-----------|--------|---------|-------------|
| Named pattern library | ❌ | ❌ | ❌ | ✅ 18 patterns |
| Pattern composition | ❌ | ❌ | ❌ | ✅ |
| Difficulty-aware routing | ❌ | ❌ | ❌ | ✅ |
| Inter-agent compression | ❌ | ❌ | ❌ | ✅ |
| Pattern-aware OTel tracing | ❌ | ❌ | ❌ | ✅ |
| Zero mandatory deps | ❌ | ❌ | ❌ | ✅ |

## Quick Start

```bash
pip install pyagent-patterns   # Core patterns (zero deps)
pip install pyagent-all        # Everything
```

```python
import asyncio
from pyagent_patterns.base import Agent, MockLLM
from pyagent_patterns.orchestration import Pipeline

llm = MockLLM(responses=["Key facts extracted", "Concise summary"])
pipeline = Pipeline(stages=[
    Agent("extractor", llm),
    Agent("summarizer", llm),
])

result = asyncio.run(pipeline.run("Process this document"))
print(result.output)  # "Concise summary"
```

## Pattern Catalog (18 patterns across 4 tiers)

### Tier 1 — Orchestration
| Pattern | LLM Calls | Best For |
|---------|-----------|----------|
| **Supervisor** | 2-3 | Task routing, customer support |
| **Pipeline** | N stages | Sequential processing, ETL |
| **Fan-Out/Fan-In** | N+1 | Parallel analysis, research |
| **Hierarchical** | 3+ levels | Enterprise workflows |
| **Orchestrator-Workers** | 1+N+1 | Dynamic task decomposition |

### Tier 2 — Resolution
| Pattern | LLM Calls | Best For |
|---------|-----------|----------|
| **Self-Reflection** | 2-6 | Code gen, writing |
| **Cross-Reflection** | 3+ | Peer review, editing |
| **Debate** | D×R+1 | Controversial decisions |
| **Voting** | N | Consensus, fault tolerance |
| **Evaluator-Optimizer** | 2-4/round | Criteria-driven quality |

### Tier 3 — Structural
| Pattern | LLM Calls | Best For |
|---------|-----------|----------|
| **Role-Based** | N×rounds | Team simulation |
| **Layered** | sum(layers) | Multi-level analysis |
| **Topology** | varies | Communication structure |
| **Blackboard** | N×rounds | Shared state coordination |

### Tier 4 — Advanced
| Pattern | LLM Calls | Best For |
|---------|-----------|----------|
| **Talker-Reasoner** | 1-2 | Cost-optimized chat |
| **Swarm** | N×rounds | Emergent behavior |
| **Human-in-the-Loop** | 1+ | Safety-critical tasks |
| **ReAct** | 1-N steps | Tool-using agents |

## Packages

| Package | Description | Install |
|---------|-------------|---------|
| **pyagent-patterns** | 18 patterns + composites + guardrails + recovery | `pip install pyagent-patterns` |
| **pyagent-router** | Difficulty scoring + cost estimation + model selection | `pip install pyagent-router` |
| **pyagent-compress** | Message compression + agent pruning + token budgets | `pip install pyagent-compress` |
| **pyagent-trace** | OTel spans + cost tracking + record/replay | `pip install pyagent-trace` |
| **pyagent-all** | Meta-package: all 4 above | `pip install pyagent-all` |

## Cross-Cutting Features

### 🔀 Routing — Pick the cheapest model that works
```python
from pyagent_router import ModelSelector
result = ModelSelector().select("What is 2+2?")
# → gpt-4.1-nano ($0.000002) instead of gpt-4o ($0.003)
```

### 📦 Compression — Reduce inter-agent token transfer
```python
from pyagent_compress import MessageCompressor
result = MessageCompressor(target_ratio=0.5).compress(verbose_text)
# → 50% fewer tokens, key information preserved
```

### 🛡️ Guardrails — Validate agent I/O
```python
from pyagent_patterns.guardrails import GuardrailChain, PIIGuard, LengthGuard
chain = GuardrailChain([PIIGuard(redact=True), LengthGuard(max_chars=5000)])
```

### 🔄 Recovery — Handle failures gracefully
```python
from pyagent_patterns.recovery import BoundedExecution
bounded = BoundedExecution(pattern=primary, fallback=cheap_fallback, timeout_seconds=30)
```

### 🧭 Advisor — Auto-select the best pattern
```python
from pyagent_patterns.advisor import PatternAdvisor, Constraints, Quality
rec = PatternAdvisor().recommend("Write code", Constraints(quality=Quality.HIGH))
# → self_reflection (generate-critique-refine loop)
```

## Running Tests

```bash
PYTHONPATH=packages/pyagent-patterns/src:packages/pyagent-router/src:packages/pyagent-compress/src:packages/pyagent-trace/src \
  python -m pytest packages/ -v
```

## Running Benchmarks

```bash
PYTHONPATH=packages/pyagent-patterns/src:packages/pyagent-router/src:packages/pyagent-compress/src:packages/pyagent-trace/src \
  python -m benchmarks.run
```

## Documentation

Full docs with Mermaid sequence diagrams, code examples, and API reference: [pyagent.dev](https://pyagent.dev)

```bash
pip install mkdocs-material mkdocstrings[python]
mkdocs serve  # Preview at http://localhost:8000
```

## License

MIT
