"""Tests for compliance checker mini-project."""
import asyncio, pytest
from pyagent_patterns.base import Agent, MockLLM
from pyagent_patterns.orchestration import Hierarchical
from pyagent_patterns.orchestration.hierarchical import Team
from pyagent_patterns.recovery import BoundedExecution


def _build_mock_pipeline(responses: list[str]) -> BoundedExecution:
    llm = MockLLM(responses=responses)
    obligation_agents = [Agent(n, llm, system_prompt="") for n in ["req_extractor", "scope"]]
    control_agents = [Agent(n, llm, system_prompt="") for n in ["policy_mapper", "evidence"]]
    pattern = Hierarchical(
        manager=Agent("director", llm, system_prompt=""),
        teams=[
            Team(name="Obligations", lead=Agent("obl_lead", llm, system_prompt=""), workers=obligation_agents),
            Team(name="Controls",    lead=Agent("ctrl_lead", llm, system_prompt=""), workers=control_agents),
        ],
    )
    return BoundedExecution(pattern=pattern,
        fallback=Agent("fallback", llm, system_prompt=""),
        max_retries=1, timeout_seconds=30.0)


def test_compliant_document_returns_compliant(compliant_responses):
    safe = _build_mock_pipeline(compliant_responses)
    result = asyncio.run(safe.run("GDPR compliance document..."))
    assert result.output


def test_non_compliant_flags_gap(non_compliant_responses):
    safe = _build_mock_pipeline(non_compliant_responses)
    result = asyncio.run(safe.run("Document missing erasure procedures..."))
    assert result.output


def test_bounded_execution_fallback():
    llm = MockLLM(responses=[], raise_after=0)
    agent = Agent("director", llm, system_prompt="")
    pattern = Hierarchical(manager=agent, teams=[])
    fallback_llm = MockLLM(responses=["Fallback: review manually."])
    safe = BoundedExecution(pattern=pattern,
        fallback=Agent("fallback", fallback_llm, system_prompt=""),
        max_retries=1, timeout_seconds=5.0)
    result = asyncio.run(safe.run("test"))
    assert result.output


def test_cost_tracker_records(bus, tracker, recorder, compliant_responses):
    tracker.record("hierarchical", "req_extractor", "claude-sonnet-4-20250514", 200, 80, 0.00120)
    tracker.record("hierarchical", "policy_mapper", "gpt-4o-mini",             150, 60, 0.00045)
    s = tracker.summary()
    assert s["total_cost_usd"] == pytest.approx(0.00165, abs=1e-5)
    assert "req_extractor" in s["by_agent"]
    assert "policy_mapper" in s["by_agent"]
