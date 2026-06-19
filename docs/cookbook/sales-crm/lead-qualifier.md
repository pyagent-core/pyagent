---
description: "How to build a multi-agent lead qualification workflow in Python with PyAgent — score, route, and draft outreach."
tags:
  - Sales & CRM
  - Supervisor
  - Pipeline
  - pyagent-patterns
---

# How to Build a Multi-Agent Lead Qualification Workflow in Python

A supervisor scores each inbound lead and routes hot leads to an outreach drafter, cold ones to nurture.

**Patterns used:** [Supervisor](../../packages/patterns/orchestration/supervisor.md)

```bash
pip install pyagent-patterns pyagent-providers
```

```python
import asyncio
from pyagent_patterns.base import Agent
from pyagent_patterns.orchestration import Supervisor
from pyagent_providers import AnthropicLLM

llm = AnthropicLLM("claude-sonnet-4-20250514")
crm = Supervisor(
    classifier=Agent("scorer", llm, system_prompt="Score the lead as hot, warm, or cold. Reply with only the label."),
    routes={
        "hot":  Agent("ae",      llm, system_prompt="Draft a personalised outreach email for this hot lead."),
        "warm": Agent("nurture", llm, system_prompt="Add this lead to a 3-touch nurture sequence; draft touch 1."),
    },
    default_route="warm",
)

async def main():
    print((await crm.run("VP Eng at a 500-person fintech, downloaded the multi-agent whitepaper twice")).output)

asyncio.run(main())
```

**Expected output:** a routed lead with drafted outreach.

## Related examples
- [Marketing Campaign Planner](../marketing-content/campaign-planner.md)

