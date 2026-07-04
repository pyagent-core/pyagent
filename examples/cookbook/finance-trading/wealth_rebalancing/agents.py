"""Agent definitions for Wealth Rebalancing Crew — system prompts verbatim from docs recipe."""
from __future__ import annotations
from pyagent_patterns.base import Agent
from pyagent_providers import AnthropicLLM, OpenAILLM


def build_agents() -> dict[str, Agent]:
    fast  = OpenAILLM("gpt-4o-mini")
    smart = AnthropicLLM("claude-sonnet-4-20250514")

    return {
        "risk_profiler": Agent(
            "risk_profiler", fast,
            system_prompt=(
                "Summarize the client mandate from the input: risk tolerance, time horizon, liquidity "
                "needs, and any hard constraints (no tobacco, ESG-only, max single-name 5%). Be explicit."
            ),
        ),
        "market_scanner": Agent(
            "market_scanner", smart,
            system_prompt=(
                "Given the mandate, assess current market regime: equity risk premium, rates direction, "
                "credit spreads, and any sector tailwinds/headwinds relevant to the portfolio."
            ),
        ),
        "allocation_strategist": Agent(
            "allocation_strategist", smart,
            system_prompt=(
                "Using the mandate and market context, propose a new target allocation: asset classes, "
                "target weights (%), and the specific trades to get there from the current holdings."
            ),
        ),
        "compliance_checker": Agent(
            "compliance_checker", fast,
            system_prompt=(
                "Review the proposed allocation against the mandate constraints. Veto any breach: "
                "single-name > 5%, excluded sectors, leverage limits. Mark COMPLIANT or list violations."
            ),
        ),
    }
