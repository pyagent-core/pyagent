"""Tests for product launch planner mini-project."""
import asyncio, pytest
from pyagent_patterns.base import Agent, MockLLM
from pyagent_patterns.orchestration import OrchestratorWorkers
from pyagent_patterns.recovery import BoundedExecution


def _build_mock(responses: list[str]) -> BoundedExecution:
    llm = MockLLM(responses=responses)
    planner = OrchestratorWorkers(
        orchestrator=Agent("launch_lead", llm, system_prompt=""),
        workers=[Agent(n, llm, system_prompt="") for n in ["pricing", "copy", "seo", "inventory"]],
    )
    return BoundedExecution(pattern=planner,
        fallback=Agent("fallback", llm, system_prompt=""),
        max_retries=1, timeout_seconds=30.0)


def test_launch_plan_returns_output(launch_responses):
    safe = _build_mock(launch_responses)
    result = asyncio.run(safe.run("Wireless keyboard, $129, launch in 2 weeks"))
    assert result.output


def test_all_workers_contribute(launch_responses):
    safe = _build_mock(launch_responses)
    result = asyncio.run(safe.run("Product brief..."))
    assert result.output


def test_cost_tracker(bus, tracker):
    tracker.record("orchestrator_workers", "pricing",    "gpt-4o-mini", 200, 80, 0.00060)
    tracker.record("orchestrator_workers", "copywriter", "gpt-4o-mini", 300, 100, 0.00080)
    tracker.record("orchestrator_workers", "seo",        "gpt-4o-mini", 150, 60, 0.00042)
    tracker.record("orchestrator_workers", "inventory",  "gpt-4o-mini", 100, 40, 0.00028)
    s = tracker.summary()
    assert s["total_cost_usd"] == pytest.approx(0.00210, abs=1e-5)
    assert len(s["by_agent"]) == 4
