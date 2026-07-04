"""Wealth Rebalancing Crew tests — deterministic, no real LLM calls."""
from __future__ import annotations
import asyncio
import pytest

from pyagent_patterns.base import Agent, MockLLM
from pyagent_patterns.orchestration import Pipeline
from pyagent_trace import CostTracker
from pyagent_trace.events import TraceEventBus

from ..models import is_compliant


def test_compliant_proposal(compliant_mock):
    pipeline = Pipeline(stages=[
        Agent(n, compliant_mock, system_prompt="")
        for n in ["risk_profiler", "market_scanner", "allocation_strategist", "compliance_checker"]
    ])
    result = asyncio.run(pipeline.run("client brief"))
    assert is_compliant(result.output)


def test_violation_flagged(violation_mock):
    pipeline = Pipeline(stages=[
        Agent(n, violation_mock, system_prompt="")
        for n in ["risk_profiler", "market_scanner", "allocation_strategist", "compliance_checker"]
    ])
    result = asyncio.run(pipeline.run("client brief"))
    assert not is_compliant(result.output)


def test_four_stages_all_called():
    calls = []
    class CountingMock(MockLLM):
        def __init__(self):
            super().__init__(responses=["r1", "r2", "r3", "COMPLIANT"])
        async def complete(self, messages):
            calls.append(True)
            return await super().complete(messages)

    mock = CountingMock()
    pipeline = Pipeline(stages=[
        Agent(n, mock, system_prompt="")
        for n in ["risk_profiler", "market_scanner", "allocation_strategist", "compliance_checker"]
    ])
    asyncio.run(pipeline.run("brief"))
    assert len(calls) == 4, "All 4 pipeline stages must call the LLM"


def test_cost_tracker():
    bus     = TraceEventBus()
    tracker = CostTracker(event_bus=bus)
    tracker.record("pipeline", "risk_profiler",        "gpt-4o-mini",   200, 80,  0.00012)
    tracker.record("pipeline", "market_scanner",       "claude-sonnet", 400, 180, 0.00320)
    tracker.record("pipeline", "allocation_strategist","claude-sonnet", 500, 200, 0.00400)
    tracker.record("pipeline", "compliance_checker",   "gpt-4o-mini",   200, 80,  0.00012)
    assert tracker.total_cost == pytest.approx(0.00744, abs=1e-5)
