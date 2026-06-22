---
description: "PyAgent core concepts — Message, Agent, Pattern, and Result: the four primitives behind every multi-agent workflow."
---

# Core Concepts

PyAgent is built on four small primitives. Once these click, every [design pattern](../packages/patterns/index.md)
and [cookbook example](../cookbook/index.md) reads the same way.

### 1. Message

The fundamental unit of communication between agents.

```python
from pyagent_patterns.base import Message

user_msg = Message.user("What is the capital of France?")
system_msg = Message.system("You are a geography expert.")
assistant_msg = Message.assistant("The capital of France is Paris.")
```

### 2. Agent

An agent wraps an LLM callable with a name and system prompt.

```python
from pyagent_patterns.base import Agent, MockLLM

# For testing: MockLLM returns canned responses
llm = MockLLM(responses=["Paris"])
agent = Agent("geography_expert", llm, system_prompt="You are a geography expert.")

# For production: any async callable (str) → str
import asyncio
result = asyncio.run(agent.run([Message.user("Capital of France?")]))
print(result.content)  # "Paris"
```

### 3. Pattern

A Pattern orchestrates one or more agents to solve a task.

```python
from pyagent_patterns.orchestration import Pipeline

pipeline = Pipeline(stages=[
    Agent("extract", llm),
    Agent("summarize", llm),
])

result = asyncio.run(pipeline.run("Process this document"))
print(result.output)           # Final output string
print(result.messages)         # All intermediate messages
print(result.metadata)         # Pattern-specific metadata
print(result.duration_seconds) # Execution time
```

### 4. Result

Every `pattern.run()` returns a `Result` with:

- **output**: Final string output
- **messages**: All intermediate `Message` objects
- **metadata**: Pattern-specific data (rounds, routes, scores, etc.)
- **duration_seconds**: Wall-clock execution time
- **token_estimate**: Estimated total tokens used

## Next

- [Quickstart](../getting-started.md) — install and run your first pattern
- [Design Patterns](../packages/patterns/index.md) — the full 18-pattern catalog
- [Cookbook](../cookbook/index.md) — complete multi-agent examples by domain
