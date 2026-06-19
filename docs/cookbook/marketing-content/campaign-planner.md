---
description: "How to build a multi-agent marketing campaign planner in Python with PyAgent — parallel channel agents aggregated into one plan."
tags:
  - Marketing & Content
  - Fan-Out / Fan-In
  - pyagent-patterns
---

# How to Build a Multi-Agent Marketing Campaign Planner in Python

Channel specialists (email, social, blog) draft in parallel, then an aggregator merges them into a single
coordinated campaign plan.

**Patterns used:** [Fan-Out / Fan-In](../../packages/patterns/orchestration/fan-out-fan-in.md)

```bash
pip install pyagent-patterns pyagent-providers
```

```python
import asyncio
from pyagent_patterns.base import Agent
from pyagent_patterns.orchestration import FanOutFanIn
from pyagent_providers import AnthropicLLM

llm = AnthropicLLM("claude-sonnet-4-20250514")

campaign = FanOutFanIn(
    workers=[
        Agent("email",  llm, system_prompt="Draft an email sequence for the launch."),
        Agent("social", llm, system_prompt="Draft a 1-week social calendar for the launch."),
        Agent("blog",   llm, system_prompt="Outline a launch blog post."),
    ],
    aggregator=Agent("planner", llm, system_prompt="Merge the channel drafts into one coordinated plan with a timeline."),
)

async def main():
    result = await campaign.run("Launch: PyAgent 1.0 — multi-agent orchestration for Python")
    print(result.output)

asyncio.run(main())
```

**Expected output:** a unified, multi-channel campaign plan with a timeline.

## Related examples

- [Research Assistant](../research-analysis/research-assistant.md) — parallel fan-out gathering

