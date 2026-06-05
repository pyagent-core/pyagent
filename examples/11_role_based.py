"""Example: Role-Based Cooperation — C-suite planning."""

import asyncio

from pyagent_patterns.base import Agent, MockLLM
from pyagent_patterns.structural import RoleBased

async def main():
    pattern = RoleBased(
        agents=[
            Agent("CEO", MockLLM(responses=["Strategy: focus on AI products", "Adjusted strategy within budget"]), system_prompt="You are the CEO"),
            Agent("CTO", MockLLM(responses=["Architecture: cloud-native", "Prioritize ML infra"]), system_prompt="You are the CTO"),
            Agent("CFO", MockLLM(responses=["Budget: $2M for Q1", "Reallocate 40% to AI"]), system_prompt="You are the CFO"),
        ],
        rounds=2,
        shared_context=True,
    )
    result = await pattern.run("Plan our product strategy for Q1")
    print(f"Output: {result.output}")
    print(f"Rounds: {result.metadata['rounds']}")

if __name__ == "__main__":
    asyncio.run(main())
