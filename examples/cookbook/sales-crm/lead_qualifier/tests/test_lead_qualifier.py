"""Tests for lead qualifier mini-project."""
import asyncio, pytest
from pyagent_patterns.base import Agent, MockLLM
from pyagent_patterns.orchestration import Supervisor, Pipeline
from pyagent_patterns.recovery import BoundedExecution
from ..models import parse_tier


def _build_mock(responses: list[str]) -> BoundedExecution:
    llm = MockLLM(responses=responses)
    router = Supervisor(
        supervisor=Agent("lead_scorer", llm, system_prompt=""),
        workers={
            "hot":  Pipeline(stages=[Agent("account_exec", llm, system_prompt="")]),
            "warm": Pipeline(stages=[Agent("nurture", llm, system_prompt="")]),
            "cold": Pipeline(stages=[Agent("cold_hold", llm, system_prompt="")]),
        },
        route_fn=lambda output, _meta: parse_tier(output),
    )
    return BoundedExecution(pattern=router,
        fallback=Agent("fallback", llm, system_prompt=""),
        max_retries=1, timeout_seconds=30.0)


def test_hot_lead_routes_to_account_exec(hot_lead_responses):
    safe = _build_mock(hot_lead_responses)
    result = asyncio.run(safe.run("TechCorp, $50k budget, VP Sales engaged"))
    assert result.output


def test_cold_lead_routes_to_cold_hold(cold_lead_responses):
    safe = _build_mock(cold_lead_responses)
    result = asyncio.run(safe.run("Unknown contact, no budget info"))
    assert result.output


def test_parse_tier_extraction():
    assert parse_tier("Lead score: 92 — HOT. Budget confirmed") == "hot"
    assert parse_tier("Score: 45 — WARM. Some interest") == "warm"
    assert parse_tier("Score: 12 — COLD. No decision maker") == "cold"
    assert parse_tier("Ambiguous response") == "warm"  # safe default


def test_cost_tracker(bus, tracker):
    tracker.record("supervisor", "lead_scorer",   "claude-sonnet-4-20250514", 300, 120, 0.00228)
    tracker.record("supervisor", "account_exec",  "gpt-4o-mini",             200,  80, 0.00060)
    s = tracker.summary()
    assert s["total_cost_usd"] == pytest.approx(0.00288, abs=1e-5)
