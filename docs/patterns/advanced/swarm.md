# Swarm Pattern

Decentralized: many agents with local rules, global behavior emerges.

## Sequence Diagram

```mermaid
sequenceDiagram
    participant A1 as Agent 1
    participant A2 as Agent 2
    participant A3 as Agent 3

    rect rgb(230, 245, 255)
        Note over A1,A3: Round 0: Independent
        A1->>A1: Form initial view
        A2->>A2: Form initial view
        A3->>A3: Form initial view
    end

    rect rgb(255, 245, 230)
        Note over A1,A3: Round 1: Neighbor interaction
        A1->>A2: Share view
        A2->>A3: Share view
        A3->>A1: Share view
        A1->>A1: Update based on A3's view
        A2->>A2: Update based on A1's view
        A3->>A3: Update based on A2's view
    end
```

## Code Example

```python
import asyncio
from pyagent_patterns.base import Agent, MockLLM
from pyagent_patterns.advanced import Swarm

pattern = Swarm(
    agents=[Agent(f"agent_{i}", MockLLM(responses=["My view on the topic"])) for i in range(5)],
    rounds=3,
    neighbor_count=2,
    aggregation="last",
)

result = asyncio.run(pattern.run("What is the most important AI trend?"))
print(f"Agents: {result.metadata['agents']}, Rounds: {result.metadata['rounds']}")
```
