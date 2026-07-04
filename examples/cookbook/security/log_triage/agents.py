"""Agent definitions for Security Log Triage — verbatim from docs recipe."""
from __future__ import annotations
from pyagent_patterns.base import Agent
from pyagent_providers import AnthropicLLM, OpenAILLM


def build_agents() -> dict[str, Agent]:
    fast  = OpenAILLM("gpt-4o-mini")
    smart = AnthropicLLM("claude-sonnet-4-20250514")

    return {
        "enricher": Agent(
            "enricher", fast,
            system_prompt=(
                "Enrich this alert with context: affected asset, business owner, data sensitivity, "
                "and a 1-5 severity. State assumptions explicitly. Pass everything forward."
            ),
        ),
        "correlator": Agent(
            "correlator", smart,
            system_prompt=(
                "Match the enriched alert against known attack patterns (MITRE ATT&CK style). "
                "Give a confidence 0-100 that this is a real attack, with the supporting signals."
            ),
        ),
        "classifier": Agent(
            "classifier", smart,
            system_prompt=(
                "Decide: FALSE_POSITIVE (confidence < 60) or ESCALATE. For ESCALATE, write a 3-line "
                "case: what happened, why it's likely real, and the recommended first response."
            ),
        ),
        "case_writer": Agent(
            "case_writer", fast,
            system_prompt=(
                "Format the triage result as a SOC case note."
            ),
        ),
    }
