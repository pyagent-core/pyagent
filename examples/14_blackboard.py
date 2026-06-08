"""Example: Blackboard — shared asynchronous state."""

import asyncio

from pyagent_patterns.base import Agent, MockLLM
from pyagent_patterns.structural import Blackboard
from pyagent_patterns.structural.blackboard import BlackboardAgent


async def main():
    pattern = Blackboard(
        agents=[
            BlackboardAgent(
                agent=Agent("alpha", MockLLM(responses=["alpha_signals: AAPL bullish, MSFT neutral"])),
                reads=["task"],
                writes=["alpha_signals"],
            ),
            BlackboardAgent(
                agent=Agent("risk", MockLLM(responses=["risk_metrics: VaR 2.3%, low vol"])),
                reads=["task", "alpha_signals"],
                writes=["risk_metrics"],
            ),
            BlackboardAgent(
                agent=Agent("portfolio", MockLLM(responses=["weights: AAPL 40%, MSFT 30%, cash 30%"])),
                reads=["alpha_signals", "risk_metrics"],
                writes=["portfolio_weights"],
            ),
        ],
        rounds=1,
    )
    result = await pattern.run("Construct optimal portfolio")
    print(f"Output: {result.output}")
    print(f"Final state keys: {list(result.metadata['final_state'].keys())}")

if __name__ == "__main__":
    asyncio.run(main())
