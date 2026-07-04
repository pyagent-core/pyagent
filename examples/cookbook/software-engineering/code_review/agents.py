"""Agent definitions for Code Review System — verbatim from docs recipe."""
from __future__ import annotations
from pyagent_patterns.base import Agent
from pyagent_providers import AnthropicLLM, OpenAILLM


def build_agents() -> dict[str, Agent]:
    fast     = OpenAILLM("gpt-4o-mini")
    smart    = AnthropicLLM("claude-sonnet-4-20250514")
    security = OpenAILLM("gpt-4o")

    return {
        "code_agent": Agent(
            "code_agent", smart,
            system_prompt=(
                "You are a senior software engineer. Review the submitted code for correctness, "
                "maintainability, and best practices. Point out specific improvements."
            ),
        ),
        "review_agent": Agent(
            "review_agent", smart,
            system_prompt=(
                "You are a code reviewer. Evaluate the code for clarity, test coverage gaps, "
                "and design concerns. Return APPROVED once the code meets the bar."
            ),
        ),
        "security_agent": Agent(
            "security_agent", security,
            system_prompt=(
                "You are a security engineer. Scan for vulnerabilities: injection flaws, "
                "broken auth, insecure deserialization, SSRF, secrets in code. "
                "Score security 1-10. If < 8, escalate to human review."
            ),
        ),
        "escalation_agent": Agent(
            "escalation_agent", fast,
            system_prompt=(
                "Summarize the security finding for human review: vulnerability type, "
                "severity, affected lines, and recommended fix."
            ),
        ),
    }


SECURITY_THRESHOLD = 8
