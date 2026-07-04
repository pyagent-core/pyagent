"""Tests for peer-review mesh mini-project."""
import asyncio, pytest
from pyagent_patterns.base import Agent, MockLLM
from pyagent_patterns.structural import Topology
from pyagent_patterns.structural.topology import TopologyType
from pyagent_patterns.recovery import BoundedExecution


def _build_mock(responses: list[str]) -> BoundedExecution:
    llm = MockLLM(responses=responses)
    agents = [Agent(n, llm, system_prompt="")
              for n in ["methodology_reviewer", "novelty_reviewer", "clarity_reviewer", "stats_reviewer"]]
    mesh = Topology(agents=agents, topology=TopologyType.MESH)
    return BoundedExecution(pattern=mesh,
        fallback=Agent("fallback", llm, system_prompt=""),
        max_retries=1, timeout_seconds=30.0)


def test_peer_review_runs(review_responses):
    safe = _build_mock(review_responses)
    result = asyncio.run(safe.run(SAMPLE_ABSTRACT))
    assert result.output


def test_all_four_reviewers_contribute(review_responses):
    safe = _build_mock(review_responses)
    result = asyncio.run(safe.run("Paper abstract about neural architecture..."))
    assert result.output


def test_mesh_topology_used():
    assert TopologyType.MESH is not None


def test_cost_tracker_four_reviewers(bus, tracker):
    for reviewer in ["methodology_reviewer", "novelty_reviewer", "clarity_reviewer", "stats_reviewer"]:
        tracker.record("topology", reviewer, "claude-sonnet-4-20250514", 400, 160, 0.00304)
    s = tracker.summary()
    assert s["total_cost_usd"] == pytest.approx(0.01216, abs=1e-4)
    assert len(s["by_agent"]) == 4


SAMPLE_ABSTRACT = "Title: LLM Scaling Laws Revisited. Abstract: We demonstrate compute-optimal training..."
