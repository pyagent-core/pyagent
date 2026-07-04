"""Agent definitions for AML Monitoring — system prompts verbatim from the docs recipe."""
from __future__ import annotations
from pyagent_patterns.base import Agent
from pyagent_providers import AnthropicLLM, OpenAILLM


def build_agents() -> dict[str, Agent]:
    fast  = OpenAILLM("gpt-4o-mini")
    smart = AnthropicLLM("claude-sonnet-4-20250514")

    return {
        "rule_screener": Agent(
            "rule_screener", fast,
            system_prompt=(
                "Screen the transaction for rule-based red flags: sanctions matches, velocity breaches "
                "(>3 transactions in 1h), structuring (amounts just under $10k), and high-risk jurisdictions. "
                "Output a bullet list of flags found (or NONE)."
            ),
        ),
        "risk_scorer": Agent(
            "risk_scorer", smart,
            system_prompt=(
                "Given the rule flags, assign a risk score 0-100 and a risk tier: "
                "Low (<30), Medium (30-70), High (>70). Explain the top two scoring drivers."
            ),
        ),
        "enrichment": Agent(
            "enrichment", fast,
            system_prompt=(
                "Enrich the alert with counterparty context: known business type, jurisdiction risk, "
                "prior SAR history. Produce a one-paragraph case summary."
            ),
        ),
        "sar_drafter": Agent(
            "sar_drafter", smart,
            system_prompt=(
                "Draft a FinCEN SAR narrative from the case summary: subject, activity description, "
                "dates, amounts, and why the activity is suspicious. Be factual and concise."
            ),
        ),
    }
