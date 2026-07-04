"""Tests for NPC world simulation mini-project."""
import asyncio, pytest
from pyagent_patterns.base import Agent, MockLLM
from pyagent_patterns.structural import Blackboard
from pyagent_patterns.structural.blackboard import BlackboardAgent
from pyagent_patterns.recovery import BoundedExecution


def _build_mock(responses: list[str]) -> BoundedExecution:
    llm = MockLLM(responses=responses)
    world = Blackboard(agents=[
        BlackboardAgent(agent=Agent("explorer",   llm, system_prompt=""), reads=["world_map"],                    writes=["world_map", "resources"]),
        BlackboardAgent(agent=Agent("builder",    llm, system_prompt=""), reads=["world_map", "resources"],       writes=["world_map", "resources"]),
        BlackboardAgent(agent=Agent("trader",     llm, system_prompt=""), reads=["resources", "world_map"],       writes=["economy"]),
        BlackboardAgent(agent=Agent("chronicler", llm, system_prompt=""), reads=["world_map", "resources", "economy"], writes=["chronicle"]),
    ], rounds=1)
    return BoundedExecution(pattern=world,
        fallback=Agent("fallback", llm, system_prompt=""),
        max_retries=1, timeout_seconds=30.0)


def test_world_simulation_runs(world_responses):
    safe = _build_mock(world_responses)
    result = asyncio.run(safe.run(DEMO_STATE))
    assert result.output


def test_chronicle_generated(world_responses):
    safe = _build_mock(world_responses)
    result = asyncio.run(safe.run(DEMO_STATE))
    assert result.output


def test_cost_tracker(bus, tracker):
    tracker.record("blackboard", "explorer",   "gpt-4o-mini", 200, 80, 0.00060)
    tracker.record("blackboard", "builder",    "gpt-4o-mini", 200, 80, 0.00060)
    tracker.record("blackboard", "trader",     "gpt-4o-mini", 150, 60, 0.00045)
    tracker.record("blackboard", "chronicler", "gpt-4o-mini", 300, 120, 0.00084)
    s = tracker.summary()
    assert s["total_cost_usd"] == pytest.approx(0.00249, abs=1e-5)
    assert set(s["by_agent"].keys()) == {"explorer", "builder", "trader", "chronicler"}


DEMO_STATE = "Forest world. Resources: 10 wood, 5 stone. Population: 3."
