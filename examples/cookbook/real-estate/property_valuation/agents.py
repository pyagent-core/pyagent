"""Agent definitions for Property Valuation — verbatim from docs recipe."""
from __future__ import annotations
from pyagent_patterns.base import Agent
from pyagent_providers import AnthropicLLM, GeminiLLM


def build_agents() -> dict[str, Agent]:
    gemini = GeminiLLM("gemini-2.5-flash")
    smart  = AnthropicLLM("claude-sonnet-4-20250514")

    return {
        "property_facts": Agent(
            "property_facts", gemini,
            system_prompt=(
                "Extract property facts: beds, baths, sqft, lot, year built, condition."
            ),
        ),
        "market_facts": Agent(
            "market_facts", gemini,
            system_prompt=(
                "Summarize the local market: median price/sqft, days on market, trend."
            ),
        ),
        "comps": Agent(
            "comps", smart,
            system_prompt=(
                "Select 3-5 comparable sales and explain why each is comparable."
            ),
        ),
        "adjustments": Agent(
            "adjustments", smart,
            system_prompt=(
                "Adjust comps for differences: sqft delta, condition, location premium."
            ),
        ),
        "report_writer": Agent(
            "report_writer", smart,
            system_prompt=(
                "Write a valuation report: estimated value range, the adjusted comps that support it, "
                "key risks, and a confidence level."
            ),
        ),
        "reviewer": Agent(
            "reviewer", smart,
            system_prompt=(
                "Sanity-check the value range against the comps; flag unsupported adjustments."
            ),
        ),
    }
