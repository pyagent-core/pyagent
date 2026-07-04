"""Agent definitions for Customer Onboarding — verbatim from docs recipe."""
from __future__ import annotations
from pyagent_patterns.base import Agent
from pyagent_providers import OpenAILLM


def build_agents() -> list[Agent]:
    fast = OpenAILLM("gpt-4o-mini")
    return [
        Agent("verification", fast,
              system_prompt=(
                  "You handle identity verification. Confirm what's needed (email, org, KYC tier) "
                  "and list any missing items. Never request more data than the plan requires."
              )),
        Agent("account_setup", fast,
              system_prompt=(
                  "You configure the account: plan, seats, integrations, and sensible defaults. "
                  "Produce a concrete setup checklist."
              )),
        Agent("faq", fast,
              system_prompt=(
                  "You answer the most common new-customer questions: billing cycle, data retention, "
                  "support SLAs, and getting-started resources. Be concise and link to docs."
              )),
        Agent("success", fast,
              system_prompt=(
                  "You handle the success hand-off: set a 30-day check-in, define the first "
                  "milestone, and provide the CSM contact. Write a warm welcome."
              )),
    ]


ROUNDS = 1
