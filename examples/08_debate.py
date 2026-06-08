"""Example: Debate — adversarial argumentation with judge."""

import asyncio

from pyagent_patterns.base import Agent, MockLLM
from pyagent_patterns.resolution import Debate


async def main():
    debate = Debate(
        debaters=[
            Agent("bull", MockLLM(responses=["Strong earnings justify premium", "Growth trajectory intact"])),
            Agent("bear", MockLLM(responses=["P/E unsustainably high", "Competition intensifying"])),
        ],
        judge=Agent("judge", MockLLM(responses=["Decision: HOLD — valid points on both sides"])),
        rounds=2,
        positions=["BUY", "SELL"],
    )
    result = await debate.run("Should we buy AAPL at current prices?")
    print(f"Output: {result.output}")
    print(f"Rounds: {result.metadata['rounds']}, Arguments: {len(result.metadata['debate_log'])}")

if __name__ == "__main__":
    asyncio.run(main())
