"""Tests for cv_screener — MockLLM only, no real LLM calls."""
from __future__ import annotations
import asyncio
import pytest

from pyagent_patterns.base import Agent, MockLLM
from pyagent_patterns.orchestration import FanOutFanIn
from pyagent_trace import CostTracker
from pyagent_trace.events import TraceEventBus

from ..models import ScreenRequest, ScreenResponse, parse_rubric_scores, parse_verdict


def test_parse_verdict_strong_hire():
    assert parse_verdict("STRONG HIRE — all criteria met.") == "STRONG HIRE"


def test_parse_verdict_no_hire():
    assert parse_verdict("NO HIRE — insufficient skills.") == "NO HIRE"


def test_parse_verdict_hire():
    assert parse_verdict("HIRE — meets most criteria.") == "HIRE"


def test_parse_rubric_scores():
    output = "Skills: 9/10. Experience: 8/10. Collaboration: 7/10."
    scores = parse_rubric_scores(output)
    assert scores.get("skills") == 9
    assert scores.get("experience") == 8
    assert scores.get("collaboration") == 7


def test_fan_out_fan_in_strong_hire():
    mock = MockLLM(responses=[
        "Skills: 9/10. Strong Python and distributed systems.",
        "Experience: 8/10. 7 years, led team.",
        "Collaboration: 8/10. Open-source maintainer.",
        "STRONG HIRE. Skills 9, Experience 8, Collaboration 8.",
    ])
    screener = FanOutFanIn(
        agents=[
            Agent("skills",       mock, system_prompt=""),
            Agent("experience",   mock, system_prompt=""),
            Agent("collaboration", mock, system_prompt=""),
        ],
        aggregator=Agent("panel", mock, system_prompt=""),
    )
    result = asyncio.run(screener.run("Senior Backend Engineer, 7 yrs..."))
    assert "HIRE" in result.output


def test_fan_out_fan_in_no_hire():
    mock = MockLLM(responses=[
        "Skills: 3/10. No Python.",
        "Experience: 4/10. Junior only.",
        "Collaboration: 5/10. Solo projects.",
        "NO HIRE. Skills score too low.",
    ])
    screener = FanOutFanIn(
        agents=[
            Agent("skills",        mock, system_prompt=""),
            Agent("experience",    mock, system_prompt=""),
            Agent("collaboration", mock, system_prompt=""),
        ],
        aggregator=Agent("panel", mock, system_prompt=""),
    )
    result = asyncio.run(screener.run("Junior developer, 1 year..."))
    assert "NO HIRE" in result.output


def test_cost_tracker_four_agents():
    bus     = TraceEventBus()
    tracker = CostTracker(event_bus=bus)
    tracker.record("cv_screener", "skills",        "claude-sonnet-4-20250514", 300, 120, 0.00255)
    tracker.record("cv_screener", "experience",    "claude-sonnet-4-20250514", 280, 110, 0.00238)
    tracker.record("cv_screener", "collaboration", "gpt-4o-mini",              200,  80, 0.00022)
    tracker.record("cv_screener", "panel",         "claude-sonnet-4-20250514", 400, 150, 0.00340)
    assert tracker.total_cost == pytest.approx(0.00855, abs=1e-5)
    assert len(tracker.by_agent()) == 4
