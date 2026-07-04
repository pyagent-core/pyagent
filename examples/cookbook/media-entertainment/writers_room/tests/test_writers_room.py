"""Tests for writers' room mini-project."""
import asyncio, pytest
from pyagent_patterns.base import Agent, MockLLM
from pyagent_patterns.coordination import RoleBased
from pyagent_patterns.recovery import BoundedExecution


def _build_mock(responses: list[str], rounds: int = 2) -> BoundedExecution:
    llm = MockLLM(responses=responses)
    agents = [Agent(n, llm, system_prompt="")
              for n in ["showrunner", "staff_writer", "script_editor", "continuity", "network_exec"]]
    room = RoleBased(agents=agents, rounds=rounds)
    return BoundedExecution(pattern=room,
        fallback=Agent("fallback", llm, system_prompt=""),
        max_retries=1, timeout_seconds=30.0)


def test_room_produces_output(room_responses):
    safe = _build_mock(room_responses)
    result = asyncio.run(safe.run("Heist thriller, power outage concept"))
    assert result.output


def test_rounds_parameter_respected(room_responses):
    safe = _build_mock(room_responses, rounds=1)
    result = asyncio.run(safe.run("Episode pitch..."))
    assert result.output


def test_cost_tracker(bus, tracker):
    tracker.record("role_based", "showrunner",    "claude-sonnet-4-20250514", 300, 120, 0.00228)
    tracker.record("role_based", "staff_writer",  "claude-haiku-4-5",         200,  80, 0.00040)
    tracker.record("role_based", "script_editor", "claude-haiku-4-5",         200,  80, 0.00040)
    s = tracker.summary()
    assert s["total_cost_usd"] == pytest.approx(0.00308, abs=1e-5)
    assert "showrunner" in s["by_agent"]
