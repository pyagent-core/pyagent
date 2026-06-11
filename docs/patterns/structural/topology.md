# Topology Pattern

Configure agent communication as Chain, Star, or Mesh graphs.

## Topology Types

```mermaid
graph LR
    subgraph Chain
        A1[A] --> A2[B] --> A3[C]
    end

    subgraph Star
        B1[Hub] --> B2[Spoke 1]
        B1 --> B3[Spoke 2]
        B1 --> B4[Spoke 3]
    end

    subgraph Mesh
        C1[A] <--> C2[B]
        C2 <--> C3[C]
        C1 <--> C3
    end
```

## Code Example

```python
import asyncio
from pyagent_patterns.base import Agent, MockLLM
from pyagent_patterns.structural import Topology, TopologyType

llm = MockLLM(responses=["Output A", "Output B", "Output C"])

# Chain topology
chain = Topology(
    agents=[Agent("A", llm), Agent("B", llm), Agent("C", llm)],
    topology=TopologyType.CHAIN,
)

# Star topology (Hub + Spokes)
star = Topology(
    agents=[Agent("Hub", llm), Agent("S1", llm), Agent("S2", llm)],
    topology=TopologyType.STAR,
    hub_index=0,
)

result = asyncio.run(chain.run("Process data through the chain"))
```
