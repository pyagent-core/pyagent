# Role-Based Cooperation

Agents with distinct roles collaborate in structured rounds.

## Sequence Diagram

```mermaid
sequenceDiagram
    participant CEO
    participant CTO
    participant CFO

    rect rgb(230, 245, 255)
        Note over CEO,CFO: Round 1
        CEO->>CEO: "Strategy: Focus on AI products"
        CTO->>CTO: "Architecture: Cloud-native microservices"
        CFO->>CFO: "Budget: $2M for Q1 initiatives"
    end

    rect rgb(230, 245, 255)
        Note over CEO,CFO: Round 2 (shared context)
        CEO->>CEO: "Adjusted: AI products within $2M budget"
        CTO->>CTO: "Revised: Prioritize ML infrastructure"
        CFO->>CFO: "Updated: Reallocate 40% to AI"
    end
```

## Code Example

```python
import asyncio
from pyagent_patterns.base import Agent, MockLLM
from pyagent_patterns.structural import RoleBased

pattern = RoleBased(
    agents=[
        Agent("CEO", MockLLM(responses=["Strategy: focus on AI"]), system_prompt="You are the CEO"),
        Agent("CTO", MockLLM(responses=["Architecture: cloud-native"]), system_prompt="You are the CTO"),
        Agent("CFO", MockLLM(responses=["Budget: $2M Q1"]), system_prompt="You are the CFO"),
    ],
    rounds=2,
    shared_context=True,
)

result = asyncio.run(pattern.run("Plan our product strategy for Q1"))
```
