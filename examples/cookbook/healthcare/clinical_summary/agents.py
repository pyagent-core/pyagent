"""Agent definitions for Clinical Summary — verbatim from docs recipe."""
from __future__ import annotations
from pyagent_patterns.base import Agent
from pyagent_providers import AnthropicLLM, OpenAILLM


def build_agents() -> dict[str, Agent]:
    fast  = OpenAILLM("gpt-4o-mini")
    smart = AnthropicLLM("claude-sonnet-4-20250514")

    return {
        "extractor": Agent(
            "extractor", fast,
            system_prompt=(
                "Extract from the clinical note as structured bullets: active diagnoses, "
                "current medications (name + dose + route), allergies, and the latest vitals. "
                "Copy values verbatim — never infer or round. Mark anything illegible as [UNREADABLE]."
            ),
        ),
        "drafter": Agent(
            "drafter", smart,
            system_prompt=(
                "Write a concise clinician-ready summary from the extracted bullets: "
                "one-line problem list, active meds, and pending follow-ups. Keep it under 150 words."
            ),
        ),
        "summary_reviewer": Agent(
            "summary_reviewer", smart,
            system_prompt=(
                "Review the draft summary against the original note. Correct any value that does not "
                "match the source, and append a SAFETY FLAGS section listing: unsupported claims, "
                "missing critical values (e.g. allergies, abnormal vitals), and dose ambiguities. "
                "Reply 'ACCURATE' on the first line when no corrections remain."
            ),
        ),
    }


STOP_PHRASE = "ACCURATE"
MAX_ROUNDS  = 2
