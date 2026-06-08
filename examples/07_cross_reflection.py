"""Example: Cross-Reflection — peer review loop."""

import asyncio

from pyagent_patterns.base import Agent, MockLLM
from pyagent_patterns.resolution import CrossReflection


async def main():
    pattern = CrossReflection(
        generator=Agent(
            "writer",
            MockLLM(
                responses=["Draft blog post about AI safety...", "Revised with stronger intro..."]
            ),
        ),
        reviewer=Agent("editor", MockLLM(responses=["Needs stronger introduction", "APPROVED"])),
        max_rounds=3,
    )
    result = await pattern.run("Write a blog post about AI safety")
    print(f"Output: {result.output}")
    print(f"Rounds: {result.metadata['rounds']}")


if __name__ == "__main__":
    asyncio.run(main())
