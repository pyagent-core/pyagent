"""Agent and tool definitions for the tool authorization recipe."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pyagent_patterns.base import Agent, LLMCallable

if TYPE_CHECKING:
    from collections.abc import Callable


def tool_vault(query: str) -> str:
    """Access confidential vault (unauthorized for analyst)."""
    return f"VAULT_SECRET_DATA({query})"


def tool_positions(query: str) -> str:
    """Query client portfolio positions."""
    return f"POSITIONS: AAPL=150, MSFT=200 for account {query}"


def tool_export(query: str) -> str:
    """Export compliance report (requires human-in-the-loop approval)."""
    return f"REPORT_EXPORTED: Successfully sent report for {query}"


def build_tools() -> dict[str, Callable[[str], str]]:
    """Return map of raw tool callables."""
    return {
        "client-vault-reader": tool_vault,
        "portfolio-data.reader": tool_positions,
        "compliance-exporter": tool_export,
    }


def build_analyst_agent(llm: LLMCallable) -> Agent:
    """Create the analyst agent."""
    return Agent(
        name="portfolio_analyst",
        llm=llm,
        system_prompt=(
            "You are a portfolio analyst. You have access to portfolio positions. "
            "Never attempt to access confidential credentials or unapproved exports."
        ),
        description="Audits portfolios and extracts asset holdings",
    )
