"""Robo-Advisor Onboarding tests — deterministic, no real LLM calls."""
from __future__ import annotations
import asyncio
import pytest

from pyagent_patterns.base import Agent
from pyagent_patterns.structural import RoleBased
from pyagent_trace import CostTracker
from pyagent_trace.events import TraceEventBus

from ..models import is_suitable


def test_suitable_result(suitable_mock):
    onboarding = RoleBased(agents=[
        Agent(n, suitable_mock, system_prompt="")
        for n in ["intake", "risk_profiler", "suitability", "planner"]
    ], rounds=1)
    result = asyncio.run(onboarding.run("client answers"))
    assert is_suitable(result.output)


def test_unsuitable_result(unsuitable_mock):
    onboarding = RoleBased(agents=[
        Agent(n, unsuitable_mock, system_prompt="")
        for n in ["intake", "risk_profiler", "suitability", "planner"]
    ], rounds=1)
    result = asyncio.run(onboarding.run("client answers"))
    assert not is_suitable(result.output)


def test_four_roles_called():
    from pyagent_patterns.base import MockLLM
    calls = []
    class CountingMock(MockLLM):
        def __init__(self):
            super().__init__(responses=["r1","r2","SUITABLE","r4"])
        async def complete(self, messages):
            calls.append(True)
            return await super().complete(messages)

    mock = CountingMock()
    onboarding = RoleBased(agents=[
        Agent(n, mock, system_prompt="")
        for n in ["intake", "risk_profiler", "suitability", "planner"]
    ], rounds=1)
    asyncio.run(onboarding.run("answers"))
    assert len(calls) == 4


def test_cost_tracker():
    bus     = TraceEventBus()
    tracker = CostTracker(event_bus=bus)
    tracker.record("role_based", "intake",        "gpt-4o-mini",   250,  80, 0.00015)
    tracker.record("role_based", "risk_profiler", "claude-sonnet", 400, 180, 0.00320)
    tracker.record("role_based", "suitability",   "gpt-4o-mini",   200,  70, 0.00012)
    tracker.record("role_based", "planner",       "claude-sonnet", 600, 250, 0.00500)
    assert tracker.total_cost == pytest.approx(0.00847, abs=1e-5)
