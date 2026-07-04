"""Agent definitions for Contract Review — verbatim from docs recipe."""
from __future__ import annotations
from pyagent_patterns.base import Agent
from pyagent_providers import AnthropicLLM


def build_agents() -> dict[str, Agent]:
    smart = AnthropicLLM("claude-sonnet-4-20250514")
    return {
        "counsel": Agent(
            "counsel", smart,
            system_prompt=(
                "You are reviewing counsel. For the clause, propose specific redlines and explain the "
                "risk each one mitigates. Be concrete: quote the language you would change."
            ),
        ),
        "partner": Agent(
            "partner", smart,
            system_prompt=(
                "You are senior reviewing partner. Critique the counsel's redlines: are they "
                "necessary, proportionate, and likely to be accepted? Return APPROVED when the "
                "review is solid."
            ),
        ),
    }


STOP_PHRASE = "APPROVED"
MAX_ROUNDS  = 3
