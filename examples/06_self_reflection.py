"""Example: Self-Reflection — generate, critique, refine."""

import asyncio

from pyagent_patterns.base import Agent, MockLLM
from pyagent_patterns.resolution import SelfReflection

async def main():
    llm = MockLLM(responses=[
        "def fib(n): return n if n<=1 else fib(n-1)+fib(n-2)",
        "Critique: naive O(2^n), needs memoization",
        "from functools import lru_cache\n@lru_cache\ndef fib(n): return n if n<=1 else fib(n-1)+fib(n-2)",
        "APPROVED — O(n) with memoization",
    ])
    pattern = SelfReflection(agent=Agent("coder", llm), max_rounds=3)
    result = await pattern.run("Write an efficient Fibonacci function")
    print(f"Output:\n{result.output}")
    print(f"Rounds: {result.metadata['rounds']}, Early stop: {result.metadata['early_stop']}")

if __name__ == "__main__":
    asyncio.run(main())
