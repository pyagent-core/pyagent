"""Tests for property valuation mini-project."""
import asyncio, pytest
from pyagent_patterns.base import Agent, MockLLM
from pyagent_patterns.structural import Layered
from pyagent_patterns.structural.layered import Layer
from pyagent_patterns.recovery import BoundedExecution


def _build_mock(responses: list[str]) -> BoundedExecution:
    llm = MockLLM(responses=responses)
    stack = Layered(layers=[
        Layer(name="gather",  agents=[Agent("data_gatherer", llm, system_prompt=""), Agent("comps_finder", llm, system_prompt="")]),
        Layer(name="analyze", agents=[Agent("market_analyst", llm, system_prompt="")]),
        Layer(name="narrate", agents=[Agent("narrative_writer", llm, system_prompt="")]),
        Layer(name="qa",      agents=[Agent("qa_reviewer", llm, system_prompt="")]),
    ])
    return BoundedExecution(pattern=stack,
        fallback=Agent("fallback", llm, system_prompt=""),
        max_retries=1, timeout_seconds=30.0)


def test_valuation_runs_four_layers(valuation_responses):
    safe = _build_mock(valuation_responses)
    result = asyncio.run(safe.run("3BR/2BA Austin TX 78704"))
    assert result.output


def test_qa_layer_runs(valuation_responses):
    safe = _build_mock(valuation_responses)
    result = asyncio.run(safe.run("Property description..."))
    assert result.output


def test_cost_tracker_all_layers(bus, tracker):
    tracker.record("layered", "data_gatherer",    "gemini-2.0-flash",          200,  80, 0.00040)
    tracker.record("layered", "comparables_finder", "gemini-2.0-flash",        250, 100, 0.00050)
    tracker.record("layered", "market_analyst",   "claude-sonnet-4-20250514",  300, 120, 0.00228)
    tracker.record("layered", "narrative_writer", "claude-sonnet-4-20250514",  350, 140, 0.00266)
    tracker.record("layered", "qa_reviewer",      "gemini-2.0-flash",          200,  80, 0.00040)
    s = tracker.summary()
    assert s["total_cost_usd"] == pytest.approx(0.00624, abs=1e-5)
    assert len(s["by_agent"]) == 5
