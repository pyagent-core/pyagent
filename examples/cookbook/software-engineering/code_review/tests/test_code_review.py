"""Tests for code_review — MockLLM only, no real LLM calls."""
from __future__ import annotations
import asyncio
import pytest

from pyagent_patterns.base import Agent, MockLLM
from pyagent_patterns.resolution import CrossReflection
from pyagent_trace import CostTracker
from pyagent_trace.events import TraceEventBus

from ..models import ReviewRequest, ReviewResponse, parse_security_score
from ..agents import SECURITY_THRESHOLD


def test_parse_security_score_explicit():
    assert parse_security_score("Security: 9/10. No issues found.") == 9


def test_parse_security_score_low():
    assert parse_security_score("Security score: 3/10. SQL injection.") == 3


def test_parse_security_score_default():
    assert parse_security_score("Code looks fine.") == 8


def test_security_threshold_constant():
    assert SECURITY_THRESHOLD == 8


def test_cross_reflection_approval():
    mock = MockLLM(responses=[
        "Variable names could be clearer.",
        "APPROVED — code is clear after refactoring.",
    ])
    review = CrossReflection(
        agents=[
            Agent("code_agent",   mock, system_prompt=""),
            Agent("review_agent", mock, system_prompt=""),
        ],
        max_rounds=3,
        stop_phrase="APPROVED",
    )
    result = asyncio.run(review.run("def get_user(id): return db.query(id)"))
    assert result is not None


def test_cost_tracker_four_agents():
    bus     = TraceEventBus()
    tracker = CostTracker(event_bus=bus)
    tracker.record("code_review", "code_agent",       "claude-sonnet-4-20250514", 400, 200, 0.00360)
    tracker.record("code_review", "review_agent",     "claude-sonnet-4-20250514", 350, 150, 0.00310)
    tracker.record("code_review", "security_agent",   "gpt-4o",                  300, 120, 0.00270)
    tracker.record("code_review", "escalation_agent", "gpt-4o-mini",             100,  40, 0.00010)
    assert tracker.total_cost == pytest.approx(0.00950, abs=1e-5)
    assert len(tracker.by_agent()) == 4


def test_review_request_schema():
    req = ReviewRequest(pr_id="PR-042", code="def foo(): pass")
    assert req.pr_id == "PR-042"


def test_review_response_not_escalated():
    resp = ReviewResponse(
        pr_id="PR-042",
        verdict="APPROVED",
        security_score=9,
        escalated=False,
        cost_usd=0.0095,
        trace_file="traces/code_review/PR-042/abc.jsonl",
    )
    assert not resp.escalated
    assert resp.security_score == 9
