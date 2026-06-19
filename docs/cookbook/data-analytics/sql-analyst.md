---
description: "How to build a multi-agent SQL analytics assistant in Python with PyAgent — a ReAct agent with cost-aware routing."
tags:
  - Data & Analytics
  - ReAct
  - Router
  - pyagent-patterns
  - pyagent-router
---

# How to Build a Multi-Agent SQL Analytics Assistant in Python

A ReAct agent reasons, writes SQL, runs it as a tool, and inspects results — with difficulty-aware routing
so simple lookups use a cheap model and hard analysis uses a strong one.

**Patterns used:** [ReAct](../../packages/patterns/advanced/react.md) ·
[Router](../../guides/router.md)

```bash
pip install pyagent-patterns pyagent-router pyagent-providers
```

```python
import asyncio
from pyagent_patterns.advanced import ReAct
from pyagent_router.middleware import RouterMiddleware
from pyagent_providers import AnthropicLLM

def run_sql(query: str) -> str:
    ...  # execute against your warehouse, return rows as text

router = RouterMiddleware(model_registry={
    "cheap":  AnthropicLLM("claude-haiku-3-5-20241022"),
    "strong": AnthropicLLM("claude-sonnet-4-20250514"),
})
analyst = router.wrap(ReAct("sql_analyst", tools=[run_sql]))

async def main():
    result = await analyst.run("Which 3 regions grew revenue fastest last quarter?")
    print(result.output)

asyncio.run(main())
```

**Expected output:** a natural-language answer backed by the SQL the agent ran.

## Related examples

- [Portfolio Review](../finance-trading/portfolio-review.md) — specialist analyst agents

