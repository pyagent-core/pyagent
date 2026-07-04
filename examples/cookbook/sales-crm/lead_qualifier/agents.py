"""Agent definitions for Lead Qualifier — verbatim from docs recipe."""
from __future__ import annotations
from pyagent_patterns.base import Agent
from pyagent_providers import AnthropicLLM, OpenAILLM


def build_agents() -> dict[str, Agent]:
    fast_llm  = OpenAILLM("gpt-4o-mini")
    smart_llm = AnthropicLLM("claude-sonnet-4-20250514")

    return {
        "scorer": Agent(
            "scorer", fast_llm,
            system_prompt=(
                "Score this inbound lead as exactly one of: hot, warm, cold. Hot = strong fit + buying "
                "signal (title, company size, intent). Warm = good fit, weak signal. Cold = poor fit or "
                "no signal. Reply with ONLY the label."
            ),
        ),
        "account_exec": Agent(
            "account_exec", smart_llm,
            system_prompt=(
                "Draft a 4-sentence personalized outreach email for this hot lead. Reference their role "
                "and the trigger that makes now the right time. End with one specific call-to-action."
            ),
        ),
        "nurture": Agent(
            "nurture", fast_llm,
            system_prompt=(
                "Add this warm lead to a 3-touch nurture sequence. Draft touch 1: a useful, no-ask "
                "message with a relevant resource. Outline touches 2 and 3 in one line each."
            ),
        ),
        "cold_hold": Agent(
            "cold_hold", fast_llm,
            system_prompt=(
                "Write a brief, polite holding reply and tag the lead for a 90-day re-check."
            ),
        ),
    }
