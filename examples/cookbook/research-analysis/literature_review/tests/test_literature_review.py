"""Tests for literature review mini-project."""
import asyncio, pytest
from pyagent_patterns.base import Agent, MockLLM
from pyagent_patterns.orchestration import Hierarchical
from pyagent_patterns.orchestration.hierarchical import Team
from pyagent_patterns.recovery import BoundedExecution


def _build_mock(responses: list[str]) -> BoundedExecution:
    llm = MockLLM(responses=responses)
    pattern = Hierarchical(
        manager=Agent("research_lead", llm, system_prompt=""),
        teams=[
            Team(name="Discovery", lead=Agent("disc_lead", llm, system_prompt=""),
                 workers=[Agent("finder", llm, system_prompt=""), Agent("triage", llm, system_prompt="")]),
            Team(name="Synthesis", lead=Agent("synth_lead", llm, system_prompt=""),
                 workers=[Agent("extractor", llm, system_prompt=""), Agent("citations", llm, system_prompt="")]),
        ],
    )
    return BoundedExecution(pattern=pattern,
        fallback=Agent("fallback", llm, system_prompt=""),
        max_retries=1, timeout_seconds=30.0)


def test_review_returns_output(review_responses):
    safe = _build_mock(review_responses)
    result = asyncio.run(safe.run("LLM scaling laws evidence"))
    assert result.output


def test_review_discovers_and_synthesizes(review_responses):
    safe = _build_mock(review_responses)
    result = asyncio.run(safe.run("Evidence for compute-optimal training"))
    assert result.output


def test_cost_tracker(bus, tracker):
    tracker.record("hierarchical", "source_finder", "claude-sonnet-4-20250514", 300, 120, 0.00180)
    tracker.record("hierarchical", "citation_writer", "gpt-4o-mini",            200,  80, 0.00060)
    s = tracker.summary()
    assert s["total_cost_usd"] == pytest.approx(0.00240, abs=1e-5)
    assert set(s["by_agent"].keys()) >= {"source_finder", "citation_writer"}
