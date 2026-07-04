"""Agent definitions for Compliance Checker — verbatim from docs recipe."""
from __future__ import annotations
from pyagent_patterns.base import Agent
from pyagent_providers import AnthropicLLM, OpenAILLM


def build_agents() -> dict[str, Agent]:
    fast  = OpenAILLM("gpt-4o-mini")
    smart = AnthropicLLM("claude-sonnet-4-20250514")

    return {
        "compliance_director": Agent(
            "compliance_director", smart,
            system_prompt=(
                "Decompose the review into obligations and controls subtasks. After both teams report, "
                "produce a gap-analysis report: each obligation, the mapped control (or NONE), a "
                "compliance status (Met/Partial/Gap), and a remediation action. Prioritize gaps by risk."
            ),
        ),
        "obligations_lead": Agent(
            "obligations_lead", fast,
            system_prompt=(
                "Extract and structure all legal obligations from the regulation. Number them."
            ),
        ),
        "controls_lead": Agent(
            "controls_lead", fast,
            system_prompt=(
                "Map each obligation to an existing policy or control. Flag gaps."
            ),
        ),
        "requirement_extractor": Agent(
            "requirement_extractor", fast,
            system_prompt=(
                "Extract every MUST/SHALL requirement from the regulation text."
            ),
        ),
        "scope_analyst": Agent(
            "scope_analyst", fast,
            system_prompt=(
                "Identify which departments, systems, and data types are in scope."
            ),
        ),
        "policy_mapper": Agent(
            "policy_mapper", fast,
            system_prompt=(
                "Map each obligation to our existing policies. Quote policy clauses."
            ),
        ),
        "evidence_checker": Agent(
            "evidence_checker", fast,
            system_prompt=(
                "Assess whether audit evidence exists for each mapped control."
            ),
        ),
    }
