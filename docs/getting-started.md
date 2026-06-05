# Getting Started

## Installation

```bash
# Core patterns only (zero LLM deps)
pip install pyagent-patterns

# With routing
pip install pyagent-router

# With compression
pip install pyagent-compress

# With tracing (requires opentelemetry)
pip install pyagent-trace

# Everything
pip install pyagent-all
```

## Core Concepts

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

## Your First Pattern

```python
import asyncio
from pyagent_patterns.base import Agent, MockLLM
from pyagent_patterns.resolution import SelfReflection

llm = MockLLM(responses=[
    "def fibonacci(n): return n if n <= 1 else fibonacci(n-1) + fibonacci(n-2)",
    "Critique: naive recursion, O(2^n). Needs memoization.",
    "from functools import lru_cache\n@lru_cache\ndef fibonacci(n): return n if n <= 1 else fibonacci(n-1) + fibonacci(n-2)",
    "APPROVED — O(n) with memoization",
])

pattern = SelfReflection(agent=Agent("coder", llm), max_rounds=3)
result = asyncio.run(pattern.run("Write an efficient Fibonacci function"))
print(result.output)
print(f"Improved in {result.metadata['rounds']} rounds")
```

## Pattern Advisor

Not sure which pattern to use? Let the advisor decide:

```python
from pyagent_patterns.advisor import PatternAdvisor, Constraints, Quality

advisor = PatternAdvisor()
rec = advisor.recommend("Write and review a legal contract", Constraints(quality=Quality.HIGH))
print(f"Use: {rec.pattern} — {rec.reason}")
print(f"Estimated calls: {rec.estimated_calls}, Cost: {rec.estimated_cost_range}")
```

## Next Steps

- [Pattern Selection Guide](patterns/index.md) — decision tree + all 18 patterns
- [Router Guide](guides/router.md) — auto-select cheapest model
- [Compression Guide](guides/compression.md) — reduce token costs
- [Tracing Guide](guides/tracing.md) — OpenTelemetry observability
