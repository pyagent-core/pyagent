"""Tests for contract_review — MockLLM only."""
from __future__ import annotations
import asyncio
import pytest

from pyagent_patterns.base import Agent, MockLLM
from pyagent_patterns.resolution import CrossReflection
from pyagent_trace import CostTracker
from pyagent_trace.events import TraceEventBus

from ..agents import MAX_ROUNDS, STOP_PHRASE
from ..models import ContractRequest, ContractResponse, parse_approved


def test_parse_approved_true():
    assert parse_approved("APPROVED — all risks addressed.") is True


def test_parse_approved_false():
    assert parse_approved("Revise: add liability cap.") is False


def test_cross_reflection_approval():
    mock = MockLLM(responses=[
        "Redline 8.2: Remove termination fee — onerous.",
        "APPROVED — redlines are proportionate.",
    ])
    review = CrossReflection(
        agents=[Agent("counsel", mock, system_prompt=""), Agent("partner", mock, system_prompt="")],
        max_rounds=MAX_ROUNDS, stop_phrase=STOP_PHRASE,
    )
    result = asyncio.run(review.run("Section 8.2: 50% termination fee..."))
    assert parse_approved(result.output)


def test_stop_phrase_constant():
    assert STOP_PHRASE == "APPROVED"


def test_cost_tracker_two_agents():
    bus = TraceEventBus(); tracker = CostTracker(event_bus=bus)
    tracker.record("contract_review", "counsel", "claude-sonnet-4-20250514", 400, 200, 0.00360)
    tracker.record("contract_review", "partner", "claude-sonnet-4-20250514", 350, 180, 0.00315)
    assert tracker.total_cost == pytest.approx(0.00675, abs=1e-5)


def test_request_schema():
    req = ContractRequest(contract_id="CTR-001", clause="Section 8.2...")
    assert req.contract_id == "CTR-001"
