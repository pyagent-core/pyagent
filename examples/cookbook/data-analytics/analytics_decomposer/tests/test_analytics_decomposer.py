"""Tests for analytics_decomposer — MockLLM only, no real LLM calls."""
from __future__ import annotations
import asyncio
import pytest

from pyagent_patterns.base import Agent, MockLLM
from pyagent_patterns.orchestration import OrchestratorWorkers
from pyagent_trace import CostTracker
from pyagent_trace.events import TraceEventBus

from ..models import AnalyticsRequest, AnalyticsResponse


def test_orchestrator_routes_to_workers():
    mock = MockLLM(responses=[
        '{"assignments": [{"worker": "query", "subtask": "churn by tier"}]}',
        "SELECT plan_tier, COUNT(*) FROM churn_events GROUP BY plan_tier.",
        "Churn concentrated in Basic tier. Workers used: query.",
    ])
    analytics = OrchestratorWorkers(
        orchestrator=Agent("analytics_lead", mock, system_prompt=""),
        workers=[
            Agent("query",     mock, system_prompt=""),
            Agent("transform", mock, system_prompt=""),
            Agent("chart",     mock, system_prompt=""),
        ],
    )
    result = asyncio.run(analytics.run("Why did churn rise in Q3?"))
    assert result is not None
    assert result.output


def test_workers_used_metadata():
    mock = MockLLM(responses=[
        '{"assignments": [{"worker": "query", "subtask": "count users"}, '
        '{"worker": "chart", "subtask": "bar chart"}]}',
        "SELECT COUNT(*) FROM users;",
        "Bar chart: x=month, y=count.",
        "Active users: 12,450. Workers: query, chart.",
    ])
    analytics = OrchestratorWorkers(
        orchestrator=Agent("analytics_lead", mock, system_prompt=""),
        workers=[
            Agent("query",     mock, system_prompt=""),
            Agent("transform", mock, system_prompt=""),
            Agent("chart",     mock, system_prompt=""),
        ],
    )
    result = asyncio.run(analytics.run("How many active users do we have?"))
    assert result is not None


def test_cost_tracker_four_agents():
    bus     = TraceEventBus()
    tracker = CostTracker(event_bus=bus)
    tracker.record("analytics_decomposer", "analytics_lead", "claude-sonnet-4-20250514", 400, 200, 0.00360)
    tracker.record("analytics_decomposer", "query",          "gpt-4o-mini",              200,  80, 0.00022)
    tracker.record("analytics_decomposer", "transform",      "gpt-4o-mini",              180,  70, 0.00019)
    tracker.record("analytics_decomposer", "chart",          "gpt-4o-mini",              150,  60, 0.00015)
    assert tracker.total_cost == pytest.approx(0.00416, abs=1e-5)
    assert len(tracker.by_agent()) == 4


def test_analytics_request_schema():
    req = AnalyticsRequest(request_id="REQ-001", question="Why did churn rise?")
    assert req.request_id == "REQ-001"
