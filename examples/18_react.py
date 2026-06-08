"""Example: ReAct — reason-act-observe with tools."""

import asyncio

from pyagent_patterns.advanced import ReAct
from pyagent_patterns.base import Agent, MockLLM


async def main():
    def search(query: str) -> str:
        return "Tim Cook has been CEO of Apple since August 2011."

    def calculator(expr: str) -> str:
        return str(eval(expr))

    pattern = ReAct(
        agent=Agent(
            "researcher",
            MockLLM(
                responses=[
                    "Thought: I need to search for the current CEO\nAction: search(CEO of Apple)",
                    "Thought: Found it. Let me calculate how long\nAction: calculator(2025 - 2011)",
                    "Thought: I have all the info\nFINISH Tim Cook has been CEO of Apple for 14 years (since 2011)",
                ]
            ),
        ),
        tools={"search": search, "calculator": calculator},
        max_steps=5,
    )
    result = await pattern.run("Who is the CEO of Apple and how long have they served?")
    print(f"Output: {result.output}")
    print(f"Steps: {result.metadata['steps']}, Tools: {result.metadata['tools_used']}")


if __name__ == "__main__":
    asyncio.run(main())
