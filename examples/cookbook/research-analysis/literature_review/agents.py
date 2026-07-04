"""Agent definitions for Literature Review — verbatim from docs recipe."""
from __future__ import annotations
from pyagent_patterns.base import Agent
from pyagent_providers import AnthropicLLM, OpenAILLM


def build_agents() -> dict[str, Agent]:
    fast  = OpenAILLM("gpt-4o-mini")
    smart = AnthropicLLM("claude-sonnet-4-20250514")

    return {
        "research_lead": Agent(
            "research_lead", smart,
            system_prompt=(
                "Decompose the question for the Discovery and Synthesis teams. After both report, write "
                "a literature review: themes, key findings with citations, points of consensus and "
                "disagreement, and a 'research gap' statement."
            ),
        ),
        "discovery_lead": Agent(
            "discovery_lead", fast,
            system_prompt=(
                "Coordinate source finding and relevance triage into a source list."
            ),
        ),
        "synthesis_lead": Agent(
            "synthesis_lead", fast,
            system_prompt=(
                "Coordinate findings extraction and citation writing into a synthesis."
            ),
        ),
        "source_finder": Agent(
            "source_finder", fast,
            system_prompt=(
                "Find 5-7 relevant papers or reports for the research question. List title, author, year."
            ),
        ),
        "relevance_triage": Agent(
            "relevance_triage", fast,
            system_prompt=(
                "Score each source 1-5 for relevance; keep only 3+ for synthesis."
            ),
        ),
        "findings_extractor": Agent(
            "findings_extractor", smart,
            system_prompt=(
                "Extract the key empirical findings from each source. Quote statistics."
            ),
        ),
        "citation_writer": Agent(
            "citation_writer", fast,
            system_prompt=(
                "Format all citations in APA style."
            ),
        ),
    }
