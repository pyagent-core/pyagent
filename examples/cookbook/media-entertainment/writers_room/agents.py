"""Agent definitions for Writers Room — verbatim from docs recipe."""
from __future__ import annotations
from pyagent_patterns.base import Agent
from pyagent_providers import AnthropicLLM


ROUNDS = 2


def build_agents() -> list[Agent]:
    sonnet = AnthropicLLM("claude-sonnet-4-20250514")
    haiku  = AnthropicLLM("claude-haiku-3-5-20241022")

    return [
        Agent(
            "showrunner", sonnet,
            system_prompt=(
                "You are the showrunner. Hold the season arc and tone. Set the episode's emotional "
                "throughline and make the final call. Update your view if a better idea surfaces."
            ),
        ),
        Agent(
            "staff_writer", sonnet,
            system_prompt=(
                "You are the staff writer. Break the premise into act beats and key scenes. Propose "
                "concrete story turns that serve the showrunner's throughline."
            ),
        ),
        Agent(
            "script_editor", haiku,
            system_prompt=(
                "You are the script editor. Tighten pacing, flag slow scenes, and sharpen the act "
                "breaks. Keep the episode to a 42-minute runtime."
            ),
        ),
        Agent(
            "continuity", haiku,
            system_prompt=(
                "You are continuity supervisor. Guard canon: character knowledge, timeline, and "
                "established facts. Suggest callbacks and flag contradictions."
            ),
        ),
        Agent(
            "network_exec", haiku,
            system_prompt=(
                "Give network notes: broad appeal, ad breaks, and standards-and-practices flags."
            ),
        ),
    ]
