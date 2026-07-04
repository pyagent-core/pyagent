"""Agent definitions for Campaign Planner — verbatim from docs recipe."""
from __future__ import annotations
from pyagent_patterns.base import Agent
from pyagent_providers import AnthropicLLM, OpenAILLM


def build_agents() -> dict[str, Agent]:
    fast_llm  = OpenAILLM("gpt-4o-mini")
    smart_llm = AnthropicLLM("claude-sonnet-4-20250514")

    return {
        "email": Agent(
            "email", fast_llm,
            system_prompt=(
                "Draft a 3-email launch sequence: teaser, launch, follow-up. Subject + 2 lines each."
            ),
        ),
        "social": Agent(
            "social", fast_llm,
            system_prompt=(
                "Draft a 1-week social calendar (LinkedIn + X): 5 posts with hooks and CTAs."
            ),
        ),
        "blog": Agent(
            "blog", fast_llm,
            system_prompt=(
                "Outline a launch blog post: title, 5 section headers, and the key takeaway."
            ),
        ),
        "campaign_director": Agent(
            "campaign_director", smart_llm,
            system_prompt=(
                "Merge the email sequence, social calendar, and blog outline into one coherent campaign "
                "brief. Add a content calendar with go-live dates. Check that messaging is consistent "
                "across all channels."
            ),
        ),
    }
