"""Example: Swarm — emergent behavior from local interactions."""

import asyncio

from pyagent_patterns.advanced import Swarm
from pyagent_patterns.base import Agent, MockLLM


async def main():
    pattern = Swarm(
        agents=[Agent(f"agent_{i}", MockLLM(responses=["My view on AI trends"])) for i in range(4)],
        rounds=2,
        neighbor_count=2,
        aggregation="last",
    )
    result = await pattern.run("What is the most important AI trend in 2025?")
    print(f"Agents: {result.metadata['agents']}, Rounds: {result.metadata['rounds']}")
    print(f"Output (first 200 chars): {result.output[:200]}...")

if __name__ == "__main__":
    asyncio.run(main())
