# Orchestrator-Workers Pattern

Central orchestrator dynamically plans subtasks, assigns them to workers, and synthesizes results.

## Sequence Diagram

```mermaid
sequenceDiagram
    participant U as User
    participant O as Orchestrator
    participant R as Researcher
    participant W as Writer
    participant E as Editor

    U->>O: "Write an essay on AI"
    O->>O: Plan: research, write, edit
    par Dynamic Assignment
        O->>R: "Research AI trends"
        O->>W: "Write introduction"
    end
    R-->>O: "Research findings..."
    W-->>O: "Introduction draft..."
    O->>E: "Edit and polish"
    E-->>O: "Polished essay"
    O-->>U: "Final essay"
```

## Code Example

```python
import asyncio
from pyagent_patterns.base import Agent, MockLLM
from pyagent_patterns.orchestration import OrchestratorWorkers

orch_llm = MockLLM(responses=[
    '{"assignments": [{"worker": "researcher", "subtask": "Research AI trends"}]}',
    "Final synthesis: AI essay based on research",
])
worker_llm = MockLLM(responses=["AI trends: transformers dominate NLP..."])

ow = OrchestratorWorkers(
    orchestrator=Agent("orchestrator", orch_llm),
    workers=[
        Agent("researcher", worker_llm, description="Finds and summarizes information"),
        Agent("writer", worker_llm, description="Writes prose and copy"),
    ],
)

result = asyncio.run(ow.run("Write a short essay on AI trends"))
print(result.output)
```

## When to Use

- ✅ **Use when:** Task requires dynamic decomposition (not known upfront)
- ✅ **Use when:** Worker pool has diverse capabilities
- ❌ **Avoid when:** Tasks always decompose the same way (use Pipeline)
