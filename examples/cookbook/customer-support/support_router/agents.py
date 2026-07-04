"""Agent definitions for Customer Support Router — verbatim from docs recipe."""
from __future__ import annotations
from pyagent_patterns.base import Agent
from pyagent_patterns.advanced import TalkerReasoner
from pyagent_providers import AnthropicLLM, OpenAILLM


def build_agents() -> dict[str, Agent | TalkerReasoner]:
    fast  = OpenAILLM("gpt-4o-mini")
    smart = AnthropicLLM("claude-sonnet-4-20250514")

    billing_bot = TalkerReasoner(
        talker=Agent("billing_fast", fast,
                     system_prompt=(
                         "You are a billing support agent. Answer quickly and clearly. "
                         "Handle: invoice questions, payment methods, refund policies, "
                         "subscription changes, and pricing. Be concise — 2-3 sentences max."
                     )),
        reasoner=Agent("billing_deep", smart,
                       system_prompt=(
                           "You are a senior billing specialist. Handle complex cases: "
                           "disputed charges, partial refunds, multi-seat subscription adjustments, "
                           "enterprise billing. Provide step-by-step resolution."
                       )),
        handoff_threshold=5,
    )

    tech_bot = TalkerReasoner(
        talker=Agent("tech_fast", fast,
                     system_prompt=(
                         "You are a tech support agent. Handle: login problems, password resets, "
                         "browser compatibility, basic integrations. Give step-by-step instructions."
                     )),
        reasoner=Agent("tech_deep", smart,
                       system_prompt=(
                           "You are a senior engineer doing technical support. Handle: API failures, "
                           "webhook debugging, performance issues, data sync, custom configs. "
                           "Ask clarifying questions if needed."
                       )),
        handoff_threshold=4,
    )

    account_bot = TalkerReasoner(
        talker=Agent("account_fast", fast,
                     system_prompt=(
                         "You are an account support agent. Handle: username changes, "
                         "email updates, team member management, permissions, SSO setup."
                     )),
        reasoner=Agent("account_deep", smart,
                       system_prompt=(
                           "You are a senior account specialist. Handle complex cases: "
                           "SAML/SSO enterprise setup, bulk user migration, "
                           "permission matrix design, compliance requirements."
                       )),
        handoff_threshold=5,
    )

    return {
        "supervisor": Agent(
            "supervisor", fast,
            system_prompt=(
                "Classify the customer query as exactly one of: billing, technical, account, escalate. "
                "Reply with only the label."
            ),
        ),
        "billing":  billing_bot,
        "technical": tech_bot,
        "account":   account_bot,
        "escalation": Agent(
            "escalation_writer", fast,
            system_prompt="Summarize the issue for human handoff: problem, attempted solutions, urgency.",
        ),
    }
