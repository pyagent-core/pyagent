"""Agent definitions for Portfolio Review — verbatim from docs recipe."""
from __future__ import annotations
from pyagent_patterns.base import Agent
from pyagent_providers import AnthropicLLM


def build_agents() -> dict[str, Agent]:
    fast  = AnthropicLLM("claude-haiku-3-5-20241022")
    smart = AnthropicLLM("claude-sonnet-4-20250514")

    return {
        "router": Agent(
            "router", fast,
            system_prompt="Classify the holding as exactly one of: equity, fixed_income, risk. Reply with only the label.",
        ),
        "equities": Agent(
            "equities", smart,
            system_prompt="Analyze the equity position: thesis, valuation multiples, key catalysts and risks.",
        ),
        "rates": Agent(
            "rates", smart,
            system_prompt="Analyze the bond position: duration, credit quality, and rate sensitivity.",
        ),
        "risk": Agent(
            "risk", smart,
            system_prompt="Assess portfolio-level risk: concentration, correlation, and tail scenarios.",
        ),
        "writer": Agent(
            "writer", smart,
            system_prompt="Write a concise investment memo from the analysis: recommendation, rationale, risks.",
        ),
        "reviewer": Agent(
            "reviewer", smart,
            system_prompt=(
                "Score the memo 1-10 against the criteria. "
                "Demand specific fixes for any criterion below bar."
            ),
        ),
    }


MEMO_CRITERIA = ["clear recommendation", "evidence-backed rationale", "explicit downside", "position sizing"]
