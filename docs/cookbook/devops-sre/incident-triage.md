---
description: "How to build a multi-agent incident triage pipeline in Python with PyAgent — log analysis, root cause, and human-gated remediation."
tags:
  - DevOps & SRE
  - Pipeline
  - Human-in-the-Loop
  - pyagent-patterns
---

# How to Build a Multi-Agent Incident Triage Pipeline in Python

A pipeline analyses logs, proposes a root cause, and drafts a remediation — pausing for human approval
before any production action.

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

triage = Pipeline(stages=[
    Agent("log_analyst",  llm, system_prompt="Summarise the error signal from these logs."),
    Agent("root_cause",   llm, system_prompt="Given the summary, hypothesise the most likely root cause."),
    Agent("remediation",  llm, system_prompt="Propose a safe, reversible remediation. Flag if it touches production."),
])

async def main():
    result = await triage.run(open("incident.log").read())
    print(result.output)   # remediation proposal — gate prod actions behind human approval

asyncio.run(main())
```

**Expected output:** a root-cause hypothesis and a reversible remediation plan, ready for a human gate.

## Related examples

- [Code Review System](../software-engineering/code-review.md) — guardrails + human escalation

