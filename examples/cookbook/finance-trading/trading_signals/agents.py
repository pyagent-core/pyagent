"""Agent definitions for Trading Signal Desk — system prompts verbatim from the docs recipe."""
from __future__ import annotations
from pyagent_patterns.base import Agent
from pyagent_providers import AnthropicLLM, GeminiLLM, OpenAILLM


def build_agents() -> dict[str, Agent]:
    fast   = OpenAILLM("gpt-4o-mini")
    smart  = AnthropicLLM("claude-sonnet-4-20250514")
    gemini = GeminiLLM("gemini-2.5-flash")

    return {
        "momentum": Agent(
            "momentum", fast,
            system_prompt=(
                "You are a momentum strategist. Analyze the market data for trend strength: "
                "price vs 20/50/200-day MAs, RSI, volume trend. "
                "Output: signal (BUY/SELL/NEUTRAL), strength (1-5), key reason."
            ),
        ),
        "mean_reversion": Agent(
            "mean_reversion", fast,
            system_prompt=(
                "You are a mean-reversion strategist. Look for overextension: z-score vs 90-day mean, "
                "Bollinger Band position, RSI extremes. "
                "Output: signal (BUY/SELL/NEUTRAL), strength (1-5), key reason."
            ),
        ),
        "sentiment": Agent(
            "sentiment", gemini,
            system_prompt=(
                "You are a sentiment strategist. Assess market mood from news/options data: "
                "put/call ratio, VIX level, news tone, analyst revision trend. "
                "Output: signal (BUY/SELL/NEUTRAL), strength (1-5), key reason."
            ),
        ),
        "signal_aggregator": Agent(
            "signal_aggregator", smart,
            system_prompt=(
                "You receive signals from three strategy agents. Weight them equally unless they conflict. "
                "Output a consensus trade idea: direction (LONG/SHORT/FLAT), conviction (1-10), "
                "entry rationale, key risk to the thesis, and suggested position size (% of book)."
            ),
        ),
    }
