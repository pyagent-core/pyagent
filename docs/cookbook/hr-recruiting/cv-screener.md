---
description: "How to build a multi-agent CV screening workflow in Python with PyAgent — parallel rubric scoring with bias guardrails."
tags:
  - HR & Recruiting
  - Fan-Out / Fan-In
  - Guardrails
  - pyagent-patterns
---

# How to Build a Multi-Agent CV Screening Workflow in Python

Independent rubric agents (skills, experience, culture-add) score a CV in parallel; an aggregator merges
the scores, and a guardrail strips protected attributes first.

**Patterns used:** [Fan-Out / Fan-In](../../packages/patterns/orchestration/fan-out-fan-in.md) ·
[Guardrails](../../guides/guardrails.md)

```bash
pip install pyagent-patterns pyagent-providers
```

```python
import asyncio
from pyagent_patterns.base import Agent
from pyagent_patterns.orchestration import FanOutFanIn
from pyagent_providers import AnthropicLLM

llm = AnthropicLLM("claude-sonnet-4-20250514")
screener = FanOutFanIn(
    workers=[
        Agent("skills",     llm, system_prompt="Score 0-10 on required technical skills with evidence."),
        Agent("experience", llm, system_prompt="Score 0-10 on relevant experience with evidence."),
        Agent("culture",    llm, system_prompt="Score 0-10 on collaboration signals with evidence."),
    ],
    aggregator=Agent("panel", llm, system_prompt="Combine the rubric scores into a hire/no-hire recommendation."),
)

async def main():
    print((await screener.run(open("cv.txt").read())).output)

asyncio.run(main())
```

**Expected output:** a combined rubric score and recommendation.

## Related examples
- [Code Review System](../software-engineering/code-review.md)

