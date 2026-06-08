"""Example: Evaluator-Optimizer — criteria-driven improvement."""

import asyncio

from pyagent_patterns.base import Agent, MockLLM
from pyagent_patterns.resolution import EvaluatorOptimizer


async def main():
    pattern = EvaluatorOptimizer(
        generator=Agent("copywriter", MockLLM(responses=["Buy now!", "Save 30% on premium headphones this week!"])),
        evaluator=Agent("critic", MockLLM(responses=[
            "SCORE: 3\nFEEDBACK: Too generic, add specifics",
            "SCORE: 8\nFEEDBACK: Specific and compelling",
        ])),
        pass_threshold=7,
        max_rounds=3,
    )
    result = await pattern.run("Write ad copy for wireless headphones")
    print(f"Output: {result.output}")
    print(f"Score: {result.metadata['final_score']}, Rounds: {result.metadata['rounds']}")

if __name__ == "__main__":
    asyncio.run(main())
