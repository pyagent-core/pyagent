"""Example: Hierarchical — manager delegates to teams."""

import asyncio

from pyagent_patterns.base import Agent, MockLLM
from pyagent_patterns.orchestration import Hierarchical
from pyagent_patterns.orchestration.hierarchical import Team


async def main():
    llm = MockLLM(
        responses=[
            "Plan: research phase, then design phase",
            "Competitor analysis done",
            "Audience insights gathered",
            "Research complete: key findings synthesized",
            "Final campaign plan ready",
        ]
    )
    h = Hierarchical(
        manager=Agent("pm", llm),
        teams=[
            Team(
                name="Research",
                lead=Agent("research_lead", llm),
                workers=[Agent("competitor", llm), Agent("audience", llm)],
            )
        ],
    )
    result = await h.run("Build a Q4 marketing campaign")
    print(f"Output: {result.output}")
    print(f"Teams: {result.metadata['teams']}, Workers: {result.metadata['total_workers']}")


if __name__ == "__main__":
    asyncio.run(main())
