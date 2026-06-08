"""Example: Topology — chain, star, and mesh communication graphs."""

import asyncio

from pyagent_patterns.base import Agent, MockLLM
from pyagent_patterns.structural import Topology, TopologyType


async def main():
    llm = MockLLM(responses=["Step A done", "Step B done", "Step C done"])

    # Chain: A → B → C
    chain = Topology(
        agents=[Agent("A", llm), Agent("B", llm), Agent("C", llm)],
        topology=TopologyType.CHAIN,
    )
    result = await chain.run("Process data through chain")
    print(f"Chain output: {result.output}")
    print(f"Topology: {result.metadata['topology']}")

    # Star: Hub + Spokes
    star = Topology(
        agents=[Agent("Hub", llm), Agent("S1", llm), Agent("S2", llm)],
        topology=TopologyType.STAR,
        hub_index=0,
    )
    result = await star.run("Analyze with star topology")
    print(f"Star output: {result.output}")


if __name__ == "__main__":
    asyncio.run(main())
