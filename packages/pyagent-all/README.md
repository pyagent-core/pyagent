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
| **pyagent-compress** | Message compression, agent pruning, interaction pruning, token budgets |
| **pyagent-trace** | OpenTelemetry spans, cost tracking, record/replay, custom attributes |

## Quick Start

```python
import asyncio
from pyagent_patterns.base import Agent, MockLLM
from pyagent_patterns.orchestration import Pipeline
from pyagent_router import ModelSelector
from pyagent_compress import MessageCompressor
from pyagent_trace import CostTracker

llm = MockLLM(responses=["Key facts extracted", "Concise summary"])
pipeline = Pipeline(stages=[
    Agent("extractor", llm),
    Agent("summarizer", llm),
])

result = asyncio.run(pipeline.run("Process this document"))
print(result.output)  # "Concise summary"
```

## Documentation

See [pyagent.dev](https://pyagent.dev) for full docs, API reference, and cookbook.
