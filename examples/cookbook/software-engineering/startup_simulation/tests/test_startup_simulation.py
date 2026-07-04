"""Tests for startup_simulation — MockLLM only, no real LLM calls."""
from __future__ import annotations
import asyncio
import pytest

from pyagent_patterns.base import Agent, MockLLM
from pyagent_patterns.structural import RoleBased
from pyagent_trace import CostTracker
from pyagent_trace.events import TraceEventBus

from ..agents import ROUNDS, build_agents
from ..models import SimulationRequest, SimulationResponse


def test_role_based_four_roles():
    mock = MockLLM(responses=[
        "PRD: standup-cli problem and user stories.",
        "Design: git-log parser, summarizer, Click CLI.",
        "Code: collect.py, group.py, summarize.py.",
        "Tests: empty repo, huge diffs, merge commits.",
        "Round 2 PRD: refined.",
        "Round 2 Design: edge cases.",
        "Round 2 Code: signatures finalized.",
        "Round 2 QA: acceptance criteria.",
    ])
    agents = [
        Agent("product_manager", mock, system_prompt=""),
        Agent("architect",       mock, system_prompt=""),
        Agent("engineer",        mock, system_prompt=""),
        Agent("qa",              mock, system_prompt=""),
    ]
    company = RoleBased(agents=agents, rounds=2)
    result = asyncio.run(company.run("Build a CLI git standup summarizer."))
    assert result is not None
    assert result.output


def test_rounds_constant():
    assert ROUNDS == 2


def test_build_agents_returns_four():
    from ..agents import build_agents as ba
    agents = ba()
    assert len(agents) == 4
    names = [a.name for a in agents]
    assert "product_manager" in names
    assert "qa" in names


def test_cost_tracker_four_roles():
    bus     = TraceEventBus()
    tracker = CostTracker(event_bus=bus)
    tracker.record("startup_simulation", "product_manager", "claude-sonnet-4-20250514", 400, 200, 0.00360)
    tracker.record("startup_simulation", "architect",       "claude-sonnet-4-20250514", 450, 220, 0.00405)
    tracker.record("startup_simulation", "engineer",        "gpt-4o",                  500, 250, 0.00450)
    tracker.record("startup_simulation", "qa",              "gpt-4o-mini",             200,  80, 0.00022)
    assert tracker.total_cost == pytest.approx(0.01237, abs=1e-5)
    assert len(tracker.by_agent()) == 4


def test_simulation_request_schema():
    req = SimulationRequest(sim_id="SIM-001", idea="Build a CLI that summarizes git activity.")
    assert req.sim_id == "SIM-001"
