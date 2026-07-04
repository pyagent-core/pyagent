"""Agent definitions for Robo-Advisor Onboarding — verbatim from docs recipe."""
from __future__ import annotations
from pyagent_patterns.base import Agent
from pyagent_providers import AnthropicLLM, OpenAILLM


def build_agents() -> list[Agent]:
    fast  = OpenAILLM("gpt-4o-mini")
    smart = AnthropicLLM("claude-sonnet-4-20250514")

    return [
        Agent(
            "intake", fast,
            system_prompt=(
                "You are the intake specialist. Extract from the client's answers: "
                "age, employment status, annual income, investable assets, primary goal "
                "(retirement / growth / income / preservation), and target timeline. "
                "Summarize clearly for the next agent."
            ),
        ),
        Agent(
            "risk_profiler", smart,
            system_prompt=(
                "You are the risk-profiling specialist. Using the intake summary, assign: "
                "risk tolerance (Conservative / Moderate / Aggressive), max drawdown comfort (%), "
                "and time horizon (years). Explain the classification in two sentences."
            ),
        ),
        Agent(
            "suitability", fast,
            system_prompt=(
                "You are the suitability analyst. Check the risk profile against regulatory "
                "suitability rules: is the proposed risk level appropriate for the client's age, "
                "income, and liquidity needs? Flag any concerns; otherwise confirm SUITABLE."
            ),
        ),
        Agent(
            "planner", smart,
            system_prompt=(
                "You are the portfolio planner. Based on the profile and suitability check, "
                "output: (1) a model allocation (asset classes + target %) that matches the risk "
                "tier, (2) a one-paragraph Investment Policy Statement (IPS), and "
                "(3) three recommended next steps for the client."
            ),
        ),
    ]
