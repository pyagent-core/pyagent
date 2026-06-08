"""Example: Voting — majority consensus."""

import asyncio

from pyagent_patterns.base import Agent, MockLLM
from pyagent_patterns.resolution import Voting


async def main():
    pattern = Voting(
        voters=[
            Agent("security", MockLLM(responses=["YES\nNo vulnerabilities found"])),
            Agent("style", MockLLM(responses=["YES\nFollows coding standards"])),
            Agent("perf", MockLLM(responses=["NO\nPotential N+1 query"])),
        ],
    )
    result = await pattern.run("Is this PR safe to merge?")
    print(f"Decision: {result.metadata['winner']}")
    print(f"Tally: {result.metadata['tally']}")


if __name__ == "__main__":
    asyncio.run(main())
