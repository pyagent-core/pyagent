"""Agent definitions for Incident Triage Pipeline — verbatim from docs recipe."""
from __future__ import annotations
from pyagent_patterns.base import Agent
from pyagent_providers import AnthropicLLM, OpenAILLM


def build_agents() -> dict[str, Agent]:
    fast  = OpenAILLM("gpt-4o-mini")
    smart = AnthropicLLM("claude-sonnet-4-20250514")

    return {
        "log_analyst": Agent(
            "log_analyst", fast,
            system_prompt=(
                "Summarize the error signal from these logs: what's failing, since when, blast radius."
            ),
        ),
        "root_cause": Agent(
            "root_cause", smart,
            system_prompt=(
                "Given the summary, give the single most likely root cause with supporting evidence."
            ),
        ),
        "remediation": Agent(
            "remediation", smart,
            system_prompt=(
                "Propose a safe, reversible remediation with exact steps and a rollback. "
                "Begin with TOUCHES_PROD: yes/no on the first line."
            ),
        ),
        "runbook_writer": Agent(
            "runbook_writer", fast,
            system_prompt=(
                "Format the remediation as a runbook step the on-call engineer can approve."
            ),
        ),
    }
