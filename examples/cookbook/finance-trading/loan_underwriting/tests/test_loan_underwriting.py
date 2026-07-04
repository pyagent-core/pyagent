"""Loan Underwriting Committee tests — deterministic, no real LLM calls."""
from __future__ import annotations
import asyncio
import pytest

from pyagent_patterns.base import Agent
from pyagent_patterns.resolution import Debate
from pyagent_trace import CostTracker
from pyagent_trace.events import TraceEventBus

from ..models import parse_decision


def test_parse_approve_with_conditions():
    assert parse_decision("APPROVE WITH CONDITIONS: personal guarantee required.") == "APPROVE WITH CONDITIONS"

def test_parse_approve():
    assert parse_decision("APPROVE: strong financials.") == "APPROVE"

def test_parse_decline():
    assert parse_decision("DECLINE: repayment risk too high.") == "DECLINE"

def test_parse_refer_default():
    assert parse_decision("Unclear outcome.") == "REFER"


def test_approve_with_conditions_result(approve_mock):
    committee = Debate(
        debaters=[
            Agent("approve_advocate", approve_mock, system_prompt=""),
            Agent("decline_advocate", approve_mock, system_prompt=""),
        ],
        judge=Agent("senior_underwriter", approve_mock, system_prompt=""),
        rounds=2,
    )
    result = asyncio.run(committee.run("loan application"))
    assert parse_decision(result.output) == "APPROVE WITH CONDITIONS"


def test_decline_result(decline_mock):
    committee = Debate(
        debaters=[
            Agent("approve_advocate", decline_mock, system_prompt=""),
            Agent("decline_advocate", decline_mock, system_prompt=""),
        ],
        judge=Agent("senior_underwriter", decline_mock, system_prompt=""),
        rounds=2,
    )
    result = asyncio.run(committee.run("loan application"))
    assert parse_decision(result.output) == "DECLINE"


def test_cost_three_agents():
    bus     = TraceEventBus()
    tracker = CostTracker(event_bus=bus)
    tracker.record("debate", "approve_advocate",   "gemini-pro",    500, 200, 0.00300)
    tracker.record("debate", "decline_advocate",   "gemini-pro",    500, 200, 0.00300)
    tracker.record("debate", "senior_underwriter", "claude-sonnet", 700, 300, 0.00600)
    assert tracker.total_cost == pytest.approx(0.01200, abs=1e-5)
