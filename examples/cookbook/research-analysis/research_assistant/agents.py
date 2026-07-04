"""Agent definitions for Research Assistant — verbatim from docs recipe."""
from __future__ import annotations
from pyagent_patterns.base import Agent
from pyagent_providers import AnthropicLLM, OpenAILLM


def build_agents() -> dict[str, Agent]:
    fast  = OpenAILLM("gpt-4o-mini")
    smart = AnthropicLLM("claude-sonnet-4-20250514")

    return {
        "web_agent": Agent(
            "web_agent", smart,
            system_prompt=(
                "You are a web research specialist. Use the search tool to gather "
                "current facts, statistics, and news about the topic. "
                "Return findings as bullet points with source URLs."
            ),
        ),
        "academic_agent": Agent(
            "academic_agent", smart,
            system_prompt=(
                "You are an academic research specialist. Search for peer-reviewed "
                "papers and studies about the topic. Cite paper titles and authors."
            ),
        ),
        "industry_agent": Agent(
            "industry_agent", fast,
            system_prompt=(
                "You are an industry analyst. Find market reports, news, and industry "
                "commentary about the topic."
            ),
        ),
        "optimist": Agent(
            "optimist", smart,
            system_prompt=(
                "Argue the most positive interpretation of the research findings. "
                "Back every claim with evidence from the sources provided."
            ),
        ),
        "sceptic": Agent(
            "sceptic", smart,
            system_prompt=(
                "Challenge the research findings with counter-evidence and limitations. "
                "Point out gaps, contradictions, and alternative explanations."
            ),
        ),
        "judge": Agent(
            "judge", smart,
            system_prompt=(
                "Weigh the optimist and sceptic arguments. Determine which claims are "
                "best supported. Produce a balanced verdict with confidence ratings."
            ),
        ),
        "synthesizer": Agent(
            "synthesizer", smart,
            system_prompt=(
                "Write a structured research report: executive summary, key findings, "
                "controversies, gaps, and citations. Keep under 500 words."
            ),
        ),
    }


def web_search(query: str) -> str:
    return f"[web results for '{query}': recent data, statistics, and analysis]"


def arxiv_search(query: str) -> str:
    return f"[arxiv results for '{query}': peer-reviewed papers on the topic]"


def news_search(query: str) -> str:
    return f"[news for '{query}': recent industry announcements and commentary]"


WEB_TOOLS     = {"web_search": web_search}
ACADEMIC_TOOLS = {"arxiv_search": arxiv_search}
INDUSTRY_TOOLS = {"news_search": news_search}
