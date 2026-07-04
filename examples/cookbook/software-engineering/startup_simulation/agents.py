"""Agent definitions for Startup Simulation — verbatim from docs recipe."""
from __future__ import annotations
from pyagent_patterns.base import Agent
from pyagent_providers import AnthropicLLM, OpenAILLM


def build_agents() -> list[Agent]:
    smart = AnthropicLLM("claude-sonnet-4-20250514")
    gpt4o = OpenAILLM("gpt-4o")
    fast  = OpenAILLM("gpt-4o-mini")

    return [
        Agent(
            "product_manager", smart,
            system_prompt=(
                "You are the Product Manager. Write a tight PRD: problem, target user, 3-5 user "
                "stories, and success metrics. Keep scope to an MVP."
            ),
        ),
        Agent(
            "architect", smart,
            system_prompt=(
                "You are the Architect. From the PRD, define components, data model, key APIs, and "
                "the tech stack. Note the single riskiest technical decision."
            ),
        ),
        Agent(
            "engineer", gpt4o,
            system_prompt=(
                "You are the Engineer. From the design, sketch the core modules and a minimal code "
                "skeleton (function/class signatures, not full bodies). Flag unknowns for QA."
            ),
        ),
        Agent(
            "qa", fast,
            system_prompt=(
                "You are QA. From the PRD and code sketch, write a test plan: critical paths, edge "
                "cases, and acceptance criteria per user story."
            ),
        ),
    ]


ROUNDS = 2
