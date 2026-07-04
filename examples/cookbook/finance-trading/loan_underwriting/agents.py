"""Agent definitions for Loan Underwriting Committee — verbatim from docs recipe."""
from __future__ import annotations
from pyagent_patterns.base import Agent
from pyagent_providers import AnthropicLLM, GeminiLLM


def build_agents() -> dict[str, Agent]:
    gemini = GeminiLLM("gemini-2.5-pro")
    smart  = AnthropicLLM("claude-sonnet-4-20250514")

    return {
        "approve_advocate": Agent(
            "approve_advocate", gemini,
            system_prompt=(
                "Argue to APPROVE this loan. Cite debt-to-income, credit history, collateral, and "
                "stable income. Pre-empt the decline case with mitigants and proposed conditions."
            ),
        ),
        "decline_advocate": Agent(
            "decline_advocate", gemini,
            system_prompt=(
                "Argue to DECLINE this loan. Focus on repayment risk, thin file, concentration, and "
                "downside scenarios. Rebut the approve case with specific counter-evidence."
            ),
        ),
        "senior_underwriter": Agent(
            "senior_underwriter", smart,
            system_prompt=(
                "You are the senior underwriter. Weigh both arguments and decide: APPROVE, "
                "APPROVE WITH CONDITIONS, or DECLINE. State the key reasons and any conditions "
                "(rate, term, collateral, covenants). Be explicit about the deciding factor."
            ),
        ),
    }
