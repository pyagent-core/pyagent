"""Tests for value-add features: recovery, guardrails, advisor."""

from __future__ import annotations

import pytest
from pyagent_patterns.advisor import Constraints, Latency, PatternAdvisor, Quality
from pyagent_patterns.base import Agent, MockLLM
from pyagent_patterns.guardrails import ContentGuard, GuardrailChain, LengthGuard, PIIGuard
from pyagent_patterns.orchestration import Pipeline
from pyagent_patterns.recovery import BoundedExecution, CircuitBreaker, CircuitState

# --- Recovery Tests ---


@pytest.mark.asyncio
async def test_bounded_execution_success():
    llm = MockLLM(responses=["Success output"])
    pattern = Pipeline(stages=[Agent("stage1", llm)])
    bounded = BoundedExecution(pattern=pattern, max_retries=2, timeout_seconds=10.0)
    result = await bounded.run("Do something")
    assert result.metadata["recovery_level"] == 0
    assert result.output == "Success output"


@pytest.mark.asyncio
async def test_bounded_execution_timeout_fallback():
    slow_llm = MockLLM(responses=["Slow response"], delay=5.0)
    fast_llm = MockLLM(responses=["Fast fallback"])
    primary = Pipeline(stages=[Agent("slow", slow_llm)])
    fallback = Pipeline(stages=[Agent("fast", fast_llm)])
    bounded = BoundedExecution(
        pattern=primary, fallback=fallback, timeout_seconds=0.1, max_retries=1
    )
    result = await bounded.run("Do something")
    assert result.metadata["recovery_level"] in (1, 2)


def test_circuit_breaker_opens_after_threshold():
    cb = CircuitBreaker(failure_threshold=2, reset_timeout_seconds=0.1)
    assert cb.state == CircuitState.CLOSED
    cb._on_failure()
    assert cb.state == CircuitState.CLOSED
    cb._on_failure()
    assert cb.state == CircuitState.OPEN


def test_circuit_breaker_resets():
    cb = CircuitBreaker(failure_threshold=1, reset_timeout_seconds=0.01)
    cb._on_failure()
    assert cb.state == CircuitState.OPEN
    import time

    time.sleep(0.02)
    assert cb.state == CircuitState.HALF_OPEN
    cb._on_success()
    assert cb.state == CircuitState.CLOSED


# --- Guardrail Tests ---


def test_length_guard_pass():
    guard = LengthGuard(max_chars=100)
    result = guard.check("Short text")
    assert result.passed is True


def test_length_guard_reject():
    guard = LengthGuard(max_chars=10, truncate=False)
    result = guard.check("This is a longer text that exceeds the limit")
    assert result.passed is False


def test_length_guard_truncate():
    guard = LengthGuard(max_chars=10, truncate=True)
    result = guard.check("This is a longer text")
    assert result.passed is True
    assert result.sanitized_content is not None
    assert len(result.sanitized_content) < len("This is a longer text") + 20


def test_pii_guard_detect_email():
    guard = PIIGuard(redact=True)
    result = guard.check("Contact me at user@example.com for details")
    assert result.passed is True
    assert "REDACTED-EMAIL" in result.sanitized_content


def test_pii_guard_reject_mode():
    guard = PIIGuard(redact=False)
    result = guard.check("My SSN is 123-45-6789")
    assert result.passed is False


def test_content_guard_deny_words():
    guard = ContentGuard(deny_words=["forbidden"])
    result = guard.check("This contains a forbidden word")
    assert result.passed is False


def test_guardrail_chain():
    chain = GuardrailChain(
        [
            LengthGuard(max_chars=1000),
            PIIGuard(redact=True),
        ]
    )
    result = chain.check("Email: test@test.com. This is fine otherwise.")
    assert result.passed is True
    assert "REDACTED" in result.sanitized_content


# --- Advisor Tests ---


def test_advisor_simple_task():
    advisor = PatternAdvisor()
    rec = advisor.recommend(
        "What is the capital of France?",
        Constraints(quality=Quality.DRAFT, latency=Latency.REALTIME),
    )
    assert rec.pattern == "pipeline"
    assert rec.estimated_calls <= 2


def test_advisor_high_quality_code():
    advisor = PatternAdvisor()
    rec = advisor.recommend(
        "Write a Python function for binary search",
        Constraints(quality=Quality.HIGH),
    )
    assert rec.pattern == "self_reflection"


def test_advisor_debate_task():
    advisor = PatternAdvisor()
    rec = advisor.recommend(
        "Compare and debate the pros and cons of microservices vs monolith",
        Constraints(quality=Quality.HIGH),
    )
    assert rec.pattern == "debate"


def test_advisor_fault_tolerant():
    advisor = PatternAdvisor()
    rec = advisor.recommend(
        "Answer this critical question",
        Constraints(fault_tolerant=True),
    )
    assert rec.pattern == "voting"


def test_advisor_budget_constrained():
    advisor = PatternAdvisor()
    rec = advisor.recommend(
        "Answer a question cheaply",
        Constraints(max_cost_usd=0.005),
    )
    assert rec.pattern == "talker_reasoner"
