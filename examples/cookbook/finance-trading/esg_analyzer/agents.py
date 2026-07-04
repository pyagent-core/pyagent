"""Agent definitions for ESG Report Analyzer — verbatim from docs recipe."""
from __future__ import annotations
from pyagent_patterns.base import Agent
from pyagent_providers import AnthropicLLM, OpenAILLM


def build_agents() -> dict[str, Agent]:
    fast  = OpenAILLM("gpt-4o-mini")
    smart = AnthropicLLM("claude-sonnet-4-20250514")

    return {
        "esg_lead": Agent(
            "esg_lead", smart,
            system_prompt=(
                "You analyze a company's ESG profile for an investor mandate. Decide which workers are "
                "needed and assign each a subtask — skip any the mandate doesn't require. Respond as JSON: "
                '{"assignments": [{"worker": "name", "subtask": "..."}]}. Then synthesize a summary with '
                "an overall ESG rating (A-E), the top strength, the top controversy, and an SFDR article fit."
            ),
        ),
        "ratings": Agent(
            "ratings", fast,
            system_prompt="Summarize the company's third-party ESG ratings and any rating disagreements.",
        ),
        "disclosure_extractor": Agent(
            "disclosure_extractor", smart,
            system_prompt="Extract the company's reported Scope 1/2/3 emissions, targets, and board-diversity data.",
        ),
        "sfdr_scorer": Agent(
            "sfdr_scorer", smart,
            system_prompt="Score alignment with SFDR/CSRD: PAI coverage, taxonomy eligibility, and gaps.",
        ),
        "controversy": Agent(
            "controversy", fast,
            system_prompt="List recent ESG controversies (labor, governance, environmental) with severity.",
        ),
    }
