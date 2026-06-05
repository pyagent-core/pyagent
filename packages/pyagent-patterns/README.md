# pyagent-patterns

**18 reusable multi-agent orchestration patterns for LLMs** — zero dependencies, async-first, fully typed.

## Install

```bash
pip install pyagent-patterns
```

## Patterns

| Tier | Patterns |
|------|----------|
| Orchestration | Supervisor, Pipeline, Fan-Out/Fan-In, Hierarchical, Orchestrator-Workers |
| Resolution | Self-Reflection, Cross-Reflection, Debate, Voting, Evaluator-Optimizer |
| Structural | Role-Based, Layered, Topology, Blackboard |
| Advanced | Talker-Reasoner, Swarm, Human-in-the-Loop, ReAct |

Plus: CompositePattern (escalation chains), PatternAdvisor, GuardrailChain, BoundedExecution, CircuitBreaker.

## Quick Example

```python
import asyncio
from pyagent_patterns.base import Agent, MockLLM
from pyagent_patterns.resolution import SelfReflection

llm = MockLLM(responses=["Draft code", "Needs error handling", "Improved code", "APPROVED"])
pattern = SelfReflection(agent=Agent("coder", llm), max_rounds=3)
result = asyncio.run(pattern.run("Write a sorting function"))
print(result.output)
```

## Documentation

Full docs: [pyagent.dev](https://pyagent.dev)
