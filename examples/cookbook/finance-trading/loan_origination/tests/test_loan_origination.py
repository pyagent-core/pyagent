"""Loan Origination Workflow tests — deterministic, no real LLM calls."""
from __future__ import annotations
import asyncio
import pytest

from pyagent_patterns.base import Agent
from pyagent_patterns.structural import Topology, TopologyType
from pyagent_trace import CostTracker
from pyagent_trace.events import TraceEventBus

from ..models import is_complete, parse_decision


def test_complete_approve(complete_approve_mock):
    chain = Topology(agents=[
        Agent(n, complete_approve_mock, system_prompt="")
        for n in ["document_collection", "income_verification", "credit_scoring", "approval"]
    ], topology=TopologyType.CHAIN)
    result = asyncio.run(chain.run("application"))
    assert parse_decision(result.output) == "APPROVE"
    assert is_complete(result.output)


def test_incomplete_refers(incomplete_refer_mock):
    chain = Topology(agents=[
        Agent(n, incomplete_refer_mock, system_prompt="")
        for n in ["document_collection", "income_verification", "credit_scoring", "approval"]
    ], topology=TopologyType.CHAIN)
    result = asyncio.run(chain.run("application"))
    assert parse_decision(result.output) == "REFER"
    assert not is_complete(result.output)


def test_cost_four_stages():
    bus     = TraceEventBus()
    tracker = CostTracker(event_bus=bus)
    tracker.record("chain", "document_collection", "gpt-4o-mini",   200,  80, 0.00012)
    tracker.record("chain", "income_verification", "gpt-4o-mini",   200,  80, 0.00012)
    tracker.record("chain", "credit_scoring",      "claude-sonnet", 400, 160, 0.00320)
    tracker.record("chain", "approval",            "claude-sonnet", 500, 200, 0.00400)
    assert tracker.total_cost == pytest.approx(0.00744, abs=1e-5)
