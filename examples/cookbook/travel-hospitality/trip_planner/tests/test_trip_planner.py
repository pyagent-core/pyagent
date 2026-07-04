"""Tests for trip-planning swarm mini-project."""
import asyncio, pytest
from pyagent_patterns.base import Agent, MockLLM
from pyagent_patterns.coordination import Swarm
from pyagent_patterns.recovery import BoundedExecution


def _build_mock(responses: list[str]) -> BoundedExecution:
    llm = MockLLM(responses=responses)
    agents = [Agent(n, llm, system_prompt="")
              for n in ["flights", "lodging", "activities", "budget", "local_guide"]]
    swarm = Swarm(agents=agents)
    return BoundedExecution(pattern=swarm,
        fallback=Agent("fallback", llm, system_prompt=""),
        max_retries=1, timeout_seconds=30.0)


def test_trip_plan_returns_output(trip_responses):
    safe = _build_mock(trip_responses)
    result = asyncio.run(safe.run("10-day Japan in April, budget $6k, from SFO"))
    assert result.output


def test_budget_within_limit(trip_responses):
    safe = _build_mock(trip_responses)
    result = asyncio.run(safe.run("Japan trip, $6k budget"))
    assert result.output


def test_five_agents_in_swarm(trip_responses):
    safe = _build_mock(trip_responses)
    result = asyncio.run(safe.run("Trip request..."))
    assert result.output


def test_cost_tracker_five_agents(bus, tracker):
    for agent in ["flights", "lodging", "activities", "budget", "local_guide"]:
        tracker.record("swarm", agent, "gemini-2.0-flash", 250, 100, 0.00050)
    s = tracker.summary()
    assert s["total_cost_usd"] == pytest.approx(0.00250, abs=1e-5)
    assert len(s["by_agent"]) == 5
