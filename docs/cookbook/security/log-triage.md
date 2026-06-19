---
description: "How to build a multi-agent security alert triage workflow in Python with PyAgent — enrich, correlate, and escalate."
tags:
  - Security & Threat Intel
  - Pipeline
  - Human-in-the-Loop
  - pyagent-patterns
---

# How to Build a Multi-Agent Security Alert Triage Workflow in Python

A pipeline enriches an alert with context, correlates it against known patterns, and escalates true
positives to a human analyst.

**Patterns used:** [Pipeline](../../packages/patterns/orchestration/pipeline.md) ·
[Human-in-the-Loop](../../packages/patterns/advanced/human-in-the-loop.md)

```bash
pip install pyagent-patterns pyagent-providers
```

```python
import asyncio
from pyagent_patterns.base import Agent
from pyagent_patterns.orchestration import Pipeline
from pyagent_providers import AnthropicLLM

llm = AnthropicLLM("claude-sonnet-4-20250514")
soc = Pipeline(stages=[
    Agent("enrich",    llm, system_prompt="Add context (asset, owner, severity) to this alert."),
    Agent("correlate", llm, system_prompt="Match against known attack patterns; estimate confidence."),
    Agent("triage",    llm, system_prompt="Classify as false-positive or escalate with a reason."),
])

async def main():
    print((await soc.run(open("alert.json").read())).output)

asyncio.run(main())
```

**Expected output:** a triage verdict with escalation reasoning.

## Related examples
- [Incident Triage Pipeline](../devops-sre/incident-triage.md)

