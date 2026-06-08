"""Example: Human-in-the-Loop — approval gates."""

import asyncio

from pyagent_patterns.advanced import HumanInTheLoop
from pyagent_patterns.advanced.human_in_the_loop import HumanDecision
from pyagent_patterns.base import Agent, MockLLM


async def main():
    call_count = 0

    def review_fn(output, metadata):
        nonlocal call_count
        call_count += 1
        print(f"  [Human Review #{call_count}]: {output[:60]}...")
        if call_count == 1:
            return HumanDecision(approved=False, feedback="Add more detail about risks")
        return HumanDecision(approved=True)

    pattern = HumanInTheLoop(
        agent=Agent(
            "writer",
            MockLLM(
                responses=[
                    "Investment thesis: AAPL is a strong buy.",
                    "Revised: AAPL is a strong buy. Key risks: valuation premium, China exposure.",
                ]
            ),
        ),
        review_fn=review_fn,
        max_revisions=3,
    )
    result = await pattern.run("Write an investment thesis for AAPL")
    print(f"Output: {result.output}")
    print(f"Approved: {result.metadata['approved']}, Revisions: {result.metadata['revisions']}")


if __name__ == "__main__":
    asyncio.run(main())
