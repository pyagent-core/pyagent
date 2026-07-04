"""Agent definitions for Loan Origination Workflow — verbatim from docs recipe."""
from __future__ import annotations
from pyagent_patterns.base import Agent
from pyagent_providers import AnthropicLLM, OpenAILLM


def build_agents() -> list[Agent]:
    fast  = OpenAILLM("gpt-4o-mini")
    smart = AnthropicLLM("claude-sonnet-4-20250514")

    return [
        Agent(
            "document_collection", fast,
            system_prompt=(
                "Stage 1 — documents. List required documents and confirm which are present. "
                "If anything mandatory is missing, mark INCOMPLETE with the reason and pass forward."
            ),
        ),
        Agent(
            "income_verification", fast,
            system_prompt=(
                "Stage 2 — income. Using the documents, verify stated income and compute DTI. "
                "Flag inconsistencies. Pass the verified figures and prior notes forward."
            ),
        ),
        Agent(
            "credit_scoring", smart,
            system_prompt=(
                "Stage 3 — credit. From the file, summarize credit history and assign a risk tier "
                "(A-E) with the key drivers. Pass everything forward."
            ),
        ),
        Agent(
            "approval", smart,
            system_prompt=(
                "Stage 4 — decision. Given documents, income, and credit tier, decide APPROVE, "
                "REFER, or DECLINE with reasons. If any earlier stage flagged INCOMPLETE, REFER."
            ),
        ),
    ]
