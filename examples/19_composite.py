"""Example: Composite pattern — escalation chain."""

import asyncio

from pyagent_patterns.base import Agent, MockLLM
from pyagent_patterns.composite import CompositePattern, min_length_check
from pyagent_patterns.resolution import SelfReflection, Voting

async def main():
    # Pattern 1: Quick reflection (may produce short output)
    reflection = SelfReflection(
        agent=Agent("coder", MockLLM(responses=["Short", "APPROVED"])),
        max_rounds=1,
    )
    # Pattern 2: Voting for more thorough answer
    voting = Voting(voters=[
        Agent("a", MockLLM(responses=["A detailed comprehensive analysis with sufficient length to pass"])),
        Agent("b", MockLLM(responses=["A detailed comprehensive analysis with sufficient length to pass"])),
    ])

    composite = CompositePattern(
        patterns=[reflection, voting],
        quality_check=min_length_check(30),
    )
    result = await composite.run("Provide a detailed analysis")
    print(f"Output: {result.output}")
    print(f"Escalation level: {result.metadata['escalation_level']}")
    print(f"Patterns tried: {result.metadata['total_patterns_tried']}")

if __name__ == "__main__":
    asyncio.run(main())
