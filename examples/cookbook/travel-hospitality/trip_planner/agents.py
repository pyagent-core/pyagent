"""Agent definitions for Trip Planner — verbatim from docs recipe."""
from __future__ import annotations
from pyagent_patterns.base import Agent
from pyagent_providers import GeminiLLM


def build_agents() -> list[Agent]:
    gemini = GeminiLLM("gemini-2.5-flash")

    return [
        Agent(
            "flights", gemini,
            system_prompt=(
                "You plan flights. Propose routes and times within budget. When neighbors change lodging "
                "or budget, adjust your picks to stay consistent."
            ),
        ),
        Agent(
            "lodging", gemini,
            system_prompt=(
                "You plan lodging near the chosen activities and airport. Update your choice when flight "
                "times or budget change."
            ),
        ),
        Agent(
            "activities", gemini,
            system_prompt=(
                "You plan day-by-day activities for the destination and dates. Keep them reachable from "
                "the lodging and within the remaining budget."
            ),
        ),
        Agent(
            "budget", gemini,
            system_prompt=(
                "You keep the trip within total budget. Flag overruns and push neighbors to trade off. "
                "Converge on a balanced allocation across flights, lodging, and activities."
            ),
        ),
        Agent(
            "local_guide", gemini,
            system_prompt=(
                "Add authentic local food and neighbourhood picks; avoid tourist traps."
            ),
        ),
    ]
