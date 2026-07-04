"""Agent definitions for Peer Review — verbatim from docs recipe."""
from __future__ import annotations
from pyagent_patterns.base import Agent
from pyagent_patterns.structural import TopologyType
from pyagent_providers import AnthropicLLM, OpenAILLM


TOPOLOGY_TYPE = TopologyType.MESH


def build_agents() -> list[Agent]:
    gpt4o  = OpenAILLM("gpt-4o")
    fast   = OpenAILLM("gpt-4o-mini")
    smart  = AnthropicLLM("claude-sonnet-4-20250514")

    return [
        Agent(
            "methodology_reviewer", smart,
            system_prompt=(
                "Review the manuscript's methods: study design, statistics, reproducibility, and threats "
                "to validity. When you see peers' notes, reconcile your view with theirs."
            ),
        ),
        Agent(
            "novelty_reviewer", gpt4o,
            system_prompt=(
                "Review the manuscript's novelty and contribution relative to prior work. Adjust your "
                "assessment when peers raise points you missed."
            ),
        ),
        Agent(
            "clarity_reviewer", fast,
            system_prompt=(
                "Review writing clarity, figures, and structure. Note where claims outrun evidence. "
                "Reconcile with peers, then help draft the consensus recommendation."
            ),
        ),
        Agent(
            "stats_reviewer", gpt4o,
            system_prompt=(
                "Check the statistics: power, multiple comparisons, and appropriate tests."
            ),
        ),
    ]
