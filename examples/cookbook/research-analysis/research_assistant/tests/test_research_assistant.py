"""Tests for research_assistant — MockLLM only, no real LLM calls."""
from __future__ import annotations
import asyncio
import pytest

from pyagent_patterns.base import Agent, MockLLM
from pyagent_patterns.orchestration import FanOutFanIn
from pyagent_patterns.resolution import Debate
from pyagent_trace import CostTracker
from pyagent_trace.events import TraceEventBus

from ..models import ResearchRequest, ResearchResponse


def test_fan_out_aggregation():
    mock = MockLLM(responses=[
        "Web: strong revenue growth.",
        "Academic: 3 papers on efficiency.",
        "Industry: new partnerships.",
        "Summary: positive outlook.",
    ])
    gather = FanOutFanIn(
        agents=[
            Agent("web_agent",      mock, system_prompt=""),
            Agent("academic_agent", mock, system_prompt=""),
            Agent("industry_agent", mock, system_prompt=""),
        ],
        aggregator=Agent("judge", mock, system_prompt=""),
    )
    result = asyncio.run(gather.run("What is the state of AI?"))
    assert result is not None
    assert result.output


def test_debate_reaches_verdict():
    mock = MockLLM(responses=[
        "Optimist: significant progress.",
        "Sceptic: benchmarks are flawed.",
        "Verdict: real progress, gaps in planning.",
    ])
    debate = Debate(
        debaters=[
            Agent("optimist", mock, system_prompt=""),
            Agent("sceptic",  mock, system_prompt=""),
        ],
        judge=Agent("judge", mock, system_prompt=""),
        rounds=1,
    )
    result = asyncio.run(debate.run("Is LLM reasoning good?"))
    assert result is not None


def test_cost_tracker_seven_agents():
    bus     = TraceEventBus()
    tracker = CostTracker(event_bus=bus)
    for name, cost in [
        ("web_agent", 0.0030), ("academic_agent", 0.0030), ("industry_agent", 0.0010),
        ("optimist", 0.0030), ("sceptic", 0.0030), ("judge", 0.0040), ("synthesizer", 0.0040),
    ]:
        tracker.record("research_assistant", name, "mock", 300, 120, cost)
    assert tracker.total_cost == pytest.approx(0.0210, abs=1e-4)
    assert len(tracker.by_agent()) == 7


def test_research_request_schema():
    req = ResearchRequest(query_id="Q-001", question="What is the state of AI reasoning?")
    assert req.query_id == "Q-001"
