"""Agent definitions for Earnings Call Analyzer — verbatim from docs recipe."""
from __future__ import annotations
from pyagent_patterns.base import Agent
from pyagent_providers import AnthropicLLM

STOP_PHRASE = "ANALYSIS COMPLETE"


def build_agents() -> dict[str, Agent]:
    smart = AnthropicLLM("claude-sonnet-4-20250514")
    return {
        "earnings_analyst": Agent(
            "earnings_analyst", smart,
            system_prompt=(
                "You analyze earnings call transcripts for buy-side investors. Each iteration:\n"
                "1. Extract: EPS beat/miss vs consensus, revenue growth YoY, and full-year guidance revision.\n"
                "2. Flag: any change in management tone (confident / cautious / evasive), and one key risk.\n"
                "3. Self-check: have you covered EPS, revenue, guidance, tone, AND risk? "
                "If any are missing or vague, note the gap and improve. "
                f'When all five are clear and specific, end with "{STOP_PHRASE}".'
            ),
        ),
    }
