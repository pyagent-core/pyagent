"""Tests for policy briefing mini-project."""
import asyncio, pytest
from pyagent_patterns.base import Agent, MockLLM
from pyagent_patterns.orchestration import Hierarchical
from pyagent_patterns.orchestration.hierarchical import Team
from pyagent_patterns.recovery import BoundedExecution


def _build_mock(responses: list[str]) -> BoundedExecution:
    llm = MockLLM(responses=responses)
    pattern = Hierarchical(
        manager=Agent("policy_director", llm, system_prompt=""),
        teams=[
            Team(name="Economics", lead=Agent("econ_lead", llm, system_prompt=""),
                 workers=[Agent("macro", llm, system_prompt=""), Agent("impact", llm, system_prompt="")]),
            Team(name="Legal",     lead=Agent("legal_lead", llm, system_prompt=""),
                 workers=[Agent("constitutional", llm, system_prompt=""), Agent("precedent", llm, system_prompt="")]),
        ],
    )
    return BoundedExecution(pattern=pattern,
        fallback=Agent("fallback", llm, system_prompt=""),
        max_retries=1, timeout_seconds=30.0)


def test_briefing_returns_output(briefing_responses):
    safe = _build_mock(briefing_responses)
    result = asyncio.run(safe.run("Carbon tax at $50/tonne"))
    assert result.output


def test_both_teams_contribute(briefing_responses):
    safe = _build_mock(briefing_responses)
    result = asyncio.run(safe.run("Minimum wage increase to $20/hr"))
    assert result.output


def test_cost_tracker(bus, tracker):
    tracker.record("hierarchical", "macro_analyst",  "claude-sonnet-4-20250514", 350, 140, 0.00265)
    tracker.record("hierarchical", "constitutional", "gpt-4o-mini",             250, 100, 0.00075)
    s = tracker.summary()
    assert s["total_cost_usd"] == pytest.approx(0.00340, abs=1e-5)
