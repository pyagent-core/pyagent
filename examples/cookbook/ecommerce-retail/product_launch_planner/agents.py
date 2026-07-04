"""Agent definitions for Product Launch Planner — verbatim from docs recipe."""
from __future__ import annotations
from pyagent_patterns.base import Agent
from pyagent_providers import AnthropicLLM, OpenAILLM


def build_agents() -> dict[str, Agent]:
    fast  = OpenAILLM("gpt-4o-mini")
    smart = AnthropicLLM("claude-sonnet-4-20250514")

    return {
        "launch_lead": Agent(
            "launch_lead", smart,
            system_prompt=(
                "You plan e-commerce product launches. From the brief, decide which specialist workers "
                "are genuinely needed and what to assign each — skip any that don't apply. Respond as "
                'JSON: {"assignments": [{"worker": "name", "subtask": "description"}]}. After all '
                "workers complete, synthesize their output into one launch plan with a go-live checklist."
            ),
        ),
        "pricing": Agent(
            "pricing", fast,
            system_prompt=(
                "Set a pricing strategy: suggested price, discount structure, and competitive positioning."
            ),
        ),
        "copywriter": Agent(
            "copywriter", fast,
            system_prompt=(
                "Write product copy: a headline, 3 bullet features, and a short description."
            ),
        ),
        "seo": Agent(
            "seo", fast,
            system_prompt=(
                "Identify 5 target keywords and suggest a meta title + meta description."
            ),
        ),
        "inventory": Agent(
            "inventory", fast,
            system_prompt=(
                "Estimate initial inventory: launch quantity, reorder point, and lead time."
            ),
        ),
    }
