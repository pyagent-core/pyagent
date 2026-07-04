"""Agent definitions for Essay Grader — verbatim from docs recipe."""
from __future__ import annotations
from pyagent_patterns.base import Agent
from pyagent_providers import AnthropicLLM, OpenAILLM, GeminiLLM


RUBRIC = (
    "Grade the essay A-F on: thesis clarity, evidence quality, argument structure, and writing style. "
    "Letter on line 1, 2-sentence rationale on line 2."
)


def build_agents() -> dict[str, Agent]:
    gpt4o      = OpenAILLM("gpt-4o")
    fast       = OpenAILLM("gpt-4o-mini")
    smart      = AnthropicLLM("claude-sonnet-4-20250514")
    gemini     = GeminiLLM("gemini-2.5-pro")

    return {
        "grader_openai": Agent(
            "grader_openai", gpt4o,
            system_prompt=RUBRIC,
        ),
        "grader_anthropic": Agent(
            "grader_anthropic", smart,
            system_prompt=RUBRIC,
        ),
        "grader_gemini": Agent(
            "grader_gemini", gemini,
            system_prompt=RUBRIC,
        ),
        "grammar_grader": Agent(
            "grammar_grader", fast,
            system_prompt=(
                "Grade ONLY grammar and mechanics A-F. Letter on line 1, reason on line 2."
            ),
        ),
    }
