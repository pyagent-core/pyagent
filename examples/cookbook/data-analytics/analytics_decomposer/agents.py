"""Agent definitions for Analytics Decomposer — verbatim from docs recipe."""
from __future__ import annotations
from pyagent_patterns.base import Agent
from pyagent_providers import AnthropicLLM, OpenAILLM


def build_agents() -> dict[str, Agent]:
    fast  = OpenAILLM("gpt-4o-mini")
    smart = AnthropicLLM("claude-sonnet-4-20250514")

    return {
        "analytics_lead": Agent(
            "analytics_lead", smart,
            system_prompt=(
                "You plan analytics work. From the request, decide which workers are needed and what to "
                'assign each — skip any that don\'t apply. Respond as JSON: '
                '{"assignments": [{"worker": "name", "subtask": "description"}]}. After workers return, '
                "synthesize a clear answer with the numbers and a recommended chart."
            ),
        ),
        "query": Agent(
            "query", fast,
            system_prompt=(
                "Write the SQL to answer the subtask. State assumptions about the schema."
            ),
        ),
        "transform": Agent(
            "transform", fast,
            system_prompt=(
                "Describe the transforms (joins, aggregations, cohorting) the analysis needs."
            ),
        ),
        "chart": Agent(
            "chart", fast,
            system_prompt=(
                "Recommend the best chart type and encodings for the result, and why."
            ),
        ),
    }
