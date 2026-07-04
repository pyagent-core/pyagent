"""Agent definitions for NPC World — verbatim from docs recipe."""
from __future__ import annotations
from pyagent_patterns.base import Agent
from pyagent_patterns.structural.blackboard import BlackboardAgent
from pyagent_providers import OpenAILLM


def build_agents() -> dict[str, BlackboardAgent]:
    fast = OpenAILLM("gpt-4o-mini")

    explorer = Agent(
        "explorer", fast,
        system_prompt=(
            "You are an explorer NPC. Scout unexplored tiles and report new terrain and resource "
            "deposits you find. Write concise structured updates."
        ),
    )
    builder = Agent(
        "builder", fast,
        system_prompt=(
            "You are a builder NPC. Using known resources, decide what to construct and where. "
            "Consume resources and add structures to the world map."
        ),
    )
    trader = Agent(
        "trader", fast,
        system_prompt=(
            "You are a trader NPC. From available resources and structures, set prices and propose "
            "trades. Update the economy with supply, demand, and prices."
        ),
    )
    chronicler = Agent(
        "chronicler", fast,
        system_prompt=(
            "Write a one-line journal entry summarising what changed this round."
        ),
    )

    return {
        "explorer": BlackboardAgent(
            agent=explorer,
            reads=["world_map"],
            writes=["world_map", "resources"],
        ),
        "builder": BlackboardAgent(
            agent=builder,
            reads=["world_map", "resources"],
            writes=["world_map", "resources"],
        ),
        "trader": BlackboardAgent(
            agent=trader,
            reads=["resources", "world_map"],
            writes=["economy"],
        ),
        "chronicler": BlackboardAgent(
            agent=chronicler,
            reads=["world_map", "resources", "economy"],
            writes=["chronicle"],
        ),
    }
