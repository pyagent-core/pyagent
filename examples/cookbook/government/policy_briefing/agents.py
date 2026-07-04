"""Agent definitions for Policy Briefing — verbatim from docs recipe."""
from __future__ import annotations
from pyagent_patterns.base import Agent
from pyagent_providers import AnthropicLLM, OpenAILLM


def build_agents() -> dict[str, Agent]:
    fast  = OpenAILLM("gpt-4o-mini")
    smart = AnthropicLLM("claude-sonnet-4-20250514")

    return {
        "policy_director": Agent(
            "policy_director", smart,
            system_prompt=(
                "Decompose the policy question into subtasks for the Economics and Legal teams. After "
                "receiving both teams' outputs, synthesize a 1-page ministerial brief: summary, options, "
                "risks, and a recommendation. Flag where teams disagree."
            ),
        ),
        "economics_lead": Agent(
            "economics_lead", fast,
            system_prompt=(
                "Coordinate the fiscal and labor analyses into one economic assessment."
            ),
        ),
        "fiscal_analyst": Agent(
            "fiscal_analyst", fast,
            system_prompt=(
                "Estimate budget impact, revenue effects, and cost over 5 years."
            ),
        ),
        "labour_analyst": Agent(
            "labour_analyst", fast,
            system_prompt=(
                "Assess employment, wage, and regional labor-market effects."
            ),
        ),
        "legal_lead": Agent(
            "legal_lead", fast,
            system_prompt=(
                "Coordinate statutory and rights analyses into one legal assessment."
            ),
        ),
        "statute_analyst": Agent(
            "statute_analyst", fast,
            system_prompt=(
                "Identify enabling legislation, required amendments, and precedent."
            ),
        ),
        "rights_analyst": Agent(
            "rights_analyst", fast,
            system_prompt=(
                "Assess civil-rights, privacy, and equality-impact considerations."
            ),
        ),
    }
