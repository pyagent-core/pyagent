"""Tests for portfolio_review — all using MockLLM, no real LLM calls."""
from __future__ import annotations
import asyncio
import pytest

from pyagent_patterns.base import Agent, MockLLM
from pyagent_patterns.orchestration import Supervisor
from pyagent_patterns.resolution import EvaluatorOptimizer
from pyagent_trace import CostTracker
from pyagent_trace.events import TraceEventBus

from ..models import parse_score, ReviewRequest, ReviewResponse
from ..agents import MEMO_CRITERIA


# ── parse_score ──────────────────────────────────────────────────────────────

def test_parse_score_explicit():
    assert parse_score("Score: 9/10 — all criteria met.") == 9


def test_parse_score_rating_keyword():
    assert parse_score("Rating: 6 — missing position sizing.") == 6


def test_parse_score_default_when_absent():
    assert parse_score("Looks good to me.") == 7


def test_parse_score_clamps_to_range():
    assert parse_score("Score: 99") == 10
    assert parse_score("Score: 0")  == 1


# ── Supervisor routing ────────────────────────────────────────────────────────

def test_equity_route_called():
    router_mock   = MockLLM(responses=["equity"])
    equities_mock = MockLLM(responses=["AAPL analysis: Buy. PE 28x reasonable."])
    rates_mock    = MockLLM(responses=["Bond analysis: duration risk high."])
    risk_mock     = MockLLM(responses=["Risk: concentrated tech."])

    desk = Supervisor(
        classifier=Agent("router",   router_mock,   system_prompt=""),
        routes={
            "equity":       Agent("equities", equities_mock, system_prompt=""),
            "fixed_income": Agent("rates",    rates_mock,    system_prompt=""),
            "risk":         Agent("risk",     risk_mock,     system_prompt=""),
        },
        default_route="risk",
    )
    result = asyncio.run(desk.run("AAPL 8% of portfolio, long equity."))
    assert "AAPL" in result.output


def test_fixed_income_route_called():
    router_mock = MockLLM(responses=["fixed_income"])
    rates_mock  = MockLLM(responses=["10Y UST: reduce duration."])

    desk = Supervisor(
        classifier=Agent("router", router_mock, system_prompt=""),
        routes={
            "equity":       Agent("equities", MockLLM(responses=[""]), system_prompt=""),
            "fixed_income": Agent("rates",    rates_mock,              system_prompt=""),
            "risk":         Agent("risk",     MockLLM(responses=[""]), system_prompt=""),
        },
        default_route="risk",
    )
    result = asyncio.run(desk.run("10Y Treasury, 5% allocation."))
    assert "UST" in result.output or "duration" in result.output.lower()


# ── EvaluatorOptimizer refinement ────────────────────────────────────────────

def test_evaluator_triggers_revision_below_threshold():
    writer_mock = MockLLM(responses=[
        "Stock is fine.",
        "Stock is fine. Downside: -20%. Position cap: 8%.",
    ])
    reviewer_mock = MockLLM(responses=[
        "Score: 4/10. Missing explicit downside and position sizing.",
        "Score: 9/10. All criteria met.",
    ])
    memo = EvaluatorOptimizer(
        generator=Agent("writer",   writer_mock,   system_prompt=""),
        evaluator=Agent("reviewer", reviewer_mock, system_prompt=""),
        criteria=MEMO_CRITERIA,
        quality_threshold=8,
        max_rounds=3,
    )
    result = asyncio.run(memo.run("Equity analysis: AAPL holds."))
    assert parse_score(result.output) >= 8


def test_evaluator_max_rounds_respected():
    writer_mock   = MockLLM(responses=["Memo draft."] * 4)
    reviewer_mock = MockLLM(responses=["Score: 3/10. Still incomplete."] * 4)
    memo = EvaluatorOptimizer(
        generator=Agent("writer",   writer_mock,   system_prompt=""),
        evaluator=Agent("reviewer", reviewer_mock, system_prompt=""),
        criteria=MEMO_CRITERIA,
        quality_threshold=8,
        max_rounds=2,
    )
    result = asyncio.run(memo.run("Any holding."))
    assert result is not None  # completes without infinite loop


# ── CostTracker ───────────────────────────────────────────────────────────────

def test_cost_tracker_records_all_six_agents():
    bus     = TraceEventBus()
    tracker = CostTracker(event_bus=bus)

    agent_costs = [
        ("router",   "claude-haiku-3-5-20241022",     50,  20, 0.00004),
        ("equities", "claude-sonnet-4-20250514",      400, 150, 0.00320),
        ("rates",    "claude-sonnet-4-20250514",      350, 130, 0.00280),
        ("risk",     "claude-sonnet-4-20250514",      300, 120, 0.00240),
        ("writer",   "claude-sonnet-4-20250514",      500, 200, 0.00400),
        ("reviewer", "claude-sonnet-4-20250514",      250,  80, 0.00190),
    ]
    for name, model, inp, out, cost in agent_costs:
        tracker.record("portfolio_review", name, model, inp, out, cost)

    assert tracker.total_cost == pytest.approx(sum(c for *_, c in agent_costs), abs=1e-6)
    assert set(tracker.by_agent().keys()) == {n for n, *_ in agent_costs}


# ── Pydantic models ───────────────────────────────────────────────────────────

def test_review_request_schema():
    req = ReviewRequest(portfolio_id="PORT-001", holding="AAPL 8% long equity")
    assert req.portfolio_id == "PORT-001"


def test_review_response_schema():
    resp = ReviewResponse(
        portfolio_id="PORT-001",
        memo="Hold AAPL. Score: 9/10.",
        score=9,
        cost_usd=0.00432,
        trace_file="traces/portfolio/PORT-001/abc123.jsonl",
    )
    assert resp.score == 9
    assert resp.cost_usd == pytest.approx(0.00432)
