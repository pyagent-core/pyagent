"""ESG Report Analyzer tests — deterministic, no real LLM calls."""
from __future__ import annotations
import asyncio
import pytest

from pyagent_patterns.base import Agent, MockLLM
from pyagent_patterns.orchestration import OrchestratorWorkers
from pyagent_trace import CostTracker
from pyagent_trace.events import TraceEventBus

from ..models import parse_rating


def test_parse_rating_b():
    assert parse_rating("ESG rating: B. Strength: net-zero.") == "B"

def test_parse_rating_fallback():
    assert parse_rating("No rating found.") == "C"


def test_orchestrator_synthesizes(esg_mock):
    esg = OrchestratorWorkers(
        orchestrator=Agent("esg_lead", esg_mock, system_prompt=""),
        workers=[
            Agent("ratings",              esg_mock, system_prompt=""),
            Agent("disclosure_extractor", esg_mock, system_prompt=""),
            Agent("sfdr_scorer",          esg_mock, system_prompt=""),
            Agent("controversy",          esg_mock, system_prompt=""),
        ],
    )
    result = asyncio.run(esg.run("ACME Industrial — SFDR Article 8 mandate"))
    assert parse_rating(result.output) in ("A", "B", "C", "D", "E")


def test_cost_tracker_five_agents():
    bus     = TraceEventBus()
    tracker = CostTracker(event_bus=bus)
    tracker.record("orch", "esg_lead",            "claude-sonnet", 600, 250, 0.00500)
    tracker.record("work", "ratings",             "gpt-4o-mini",   300, 100, 0.00020)
    tracker.record("work", "disclosure_extractor","claude-sonnet", 400, 180, 0.00340)
    tracker.record("work", "sfdr_scorer",         "claude-sonnet", 400, 180, 0.00340)
    tracker.record("work", "controversy",         "gpt-4o-mini",   250,  80, 0.00015)
    assert tracker.total_cost == pytest.approx(0.01215, abs=1e-5)
    assert len(tracker.by_agent()) == 5
