---
description: "How to build a multi-agent clinical note summarizer in Python with PyAgent — extract, summarize, and safety-check."
tags:
  - Healthcare & Life Sciences
  - Pipeline
  - Self-Reflection
  - pyagent-patterns
---

# How to Build a Multi-Agent Clinical Note Summarizer in Python

A pipeline extracts structured findings, summarizes them, and runs a self-reflection safety pass before
anything reaches a clinician.

**Patterns used:** [Pipeline](../../packages/patterns/orchestration/pipeline.md) ·
[Self-Reflection](../../packages/patterns/resolution/self-reflection.md)

```bash
pip install pyagent-patterns pyagent-providers
```

```python
import asyncio
from pyagent_patterns.base import Agent
from pyagent_patterns.orchestration import Pipeline
from pyagent_providers import AnthropicLLM

llm = AnthropicLLM("claude-sonnet-4-20250514")
summarizer = Pipeline(stages=[
    Agent("extract",  llm, system_prompt="Extract diagnoses, meds, and vitals as structured bullets."),
    Agent("summarize",llm, system_prompt="Write a concise clinical summary from the bullets."),
    Agent("safety",   llm, system_prompt="Flag any unsupported claim or missing critical value."),
])

async def main():
    print((await summarizer.run(open("note.txt").read())).output)

asyncio.run(main())
```

**Expected output:** a clinician-ready summary with safety flags.

## Related examples
- [Contract Review Assistant](../legal-compliance/contract-review.md) — review-before-signoff

