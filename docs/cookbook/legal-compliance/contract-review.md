---
description: "How to build a multi-agent contract review assistant in Python with PyAgent — drafter plus an independent reviewer with guardrails."
tags:
  - Legal & Compliance
  - Cross-Reflection
  - Guardrails
  - pyagent-patterns
---

# How to Build a Multi-Agent Contract Review Assistant in Python

A drafter proposes redlines and an independent reviewer agent critiques them — cross-reflection that
surfaces risky clauses before a human signs off.

**Patterns used:** [Cross-Reflection](../../packages/patterns/resolution/cross-reflection.md) ·
[Guardrails](../../guides/guardrails.md)

```bash
pip install pyagent-patterns pyagent-providers
```

```python
import asyncio
from pyagent_patterns.base import Agent
from pyagent_patterns.resolution import CrossReflection
from pyagent_providers import AnthropicLLM

llm = AnthropicLLM("claude-sonnet-4-20250514")

review = CrossReflection(
    generator=Agent("counsel", llm, system_prompt="Propose redlines for the clause; note the risk."),
    reviewer=Agent("partner", llm, system_prompt="Critique the redlines; flag anything that increases liability."),
    max_rounds=2,
)

async def main():
    result = await review.run("Limitation of liability capped at fees paid in the prior 3 months.")
    print(result.output)   # reviewed redlines — surface to a human for final sign-off

asyncio.run(main())
```

**Expected output:** reviewed redlines with liability flags, ready for human sign-off.

## Related examples

- [Customer Support Router](../customer-support/support-router.md) — guardrails + escalation

