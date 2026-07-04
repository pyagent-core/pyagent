"""Agent definitions for CV Screener — verbatim from docs recipe."""
from __future__ import annotations
from pyagent_patterns.base import Agent
from pyagent_providers import AnthropicLLM, OpenAILLM


def build_agents() -> dict[str, Agent]:
    fast  = OpenAILLM("gpt-4o-mini")
    smart = AnthropicLLM("claude-sonnet-4-20250514")

    return {
        "skills": Agent(
            "skills", smart,
            system_prompt=(
                "Score 0-10 on the required technical skills. Quote evidence from the CV."
            ),
        ),
        "experience": Agent(
            "experience", smart,
            system_prompt=(
                "Score 0-10 on relevant experience and impact. Quote evidence."
            ),
        ),
        "collaboration": Agent(
            "collaboration", fast,
            system_prompt=(
                "Score 0-10 on collaboration and ownership signals. Quote evidence."
            ),
        ),
        "panel": Agent(
            "panel", smart,
            system_prompt=(
                "Combine the three rubric scores into one recommendation: STRONG HIRE / HIRE / NO HIRE. "
                "Show each rubric score, the overall, and the single biggest risk."
            ),
        ),
    }
