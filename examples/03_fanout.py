"""Example: Fan-Out/Fan-In — parallel stock analysis."""

import asyncio

from pyagent_patterns.base import Agent, MockLLM
from pyagent_patterns.orchestration import FanOutFanIn

async def main():
    fanout = FanOutFanIn(
        agents=[
            Agent("fundamentals", MockLLM(responses=["P/E: 28, revenue growth 15%"])),
            Agent("technicals", MockLLM(responses=["RSI: 65, MACD bullish crossover"])),
            Agent("sentiment", MockLLM(responses=["85% positive social sentiment"])),
        ],
        aggregator=Agent("aggregator", MockLLM(responses=["Combined: Strong BUY signal"])),
    )
    result = await fanout.run("Analyze AAPL stock")
    print(f"Output: {result.output}")
    print(f"Parallel agents: {result.metadata['parallel_agents']}")

if __name__ == "__main__":
    asyncio.run(main())
