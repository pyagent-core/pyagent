"""Tests for support_router — MockLLM only, no real LLM calls."""
from __future__ import annotations
import asyncio
import pytest

from pyagent_patterns.base import Agent, MockLLM
from pyagent_patterns.orchestration import Supervisor
from pyagent_trace import CostTracker
from pyagent_trace.events import TraceEventBus

from ..models import parse_intent, SupportRequest, SupportResponse


# ── parse_intent ─────────────────────────────────────────────────────────────

def test_parse_intent_billing():
    assert parse_intent("billing") == "billing"


def test_parse_intent_technical():
    assert parse_intent("  Technical issue  ") == "technical"


def test_parse_intent_defaults_to_escalate():
    assert parse_intent("please help") == "escalate"


# ── Supervisor routing ────────────────────────────────────────────────────────

def test_billing_route():
    router_mock  = MockLLM(responses=["billing"])
    billing_mock = MockLLM(responses=["Your duplicate charge will be refunded within 3-5 days."])

    desk = Supervisor(
        classifier=Agent("supervisor",   router_mock,  system_prompt=""),
        routes={
            "billing":   Agent("billing",   billing_mock, system_prompt=""),
            "technical": Agent("technical", MockLLM(responses=[""]), system_prompt=""),
            "account":   Agent("account",   MockLLM(responses=[""]), system_prompt=""),
        },
        default_route="escalate",
    )
    result = asyncio.run(desk.run("I was charged twice for my subscription."))
    assert "refund" in result.output.lower() or "charge" in result.output.lower()


def test_technical_route():
    router_mock = MockLLM(responses=["technical"])
    tech_mock   = MockLLM(responses=["To reset your password, go to Settings > Security."])

    desk = Supervisor(
        classifier=Agent("supervisor",  router_mock, system_prompt=""),
        routes={
            "billing":   Agent("billing",   MockLLM(responses=[""]), system_prompt=""),
            "technical": Agent("technical", tech_mock,               system_prompt=""),
            "account":   Agent("account",   MockLLM(responses=[""]), system_prompt=""),
        },
        default_route="escalate",
    )
    result = asyncio.run(desk.run("I can't log in to my account."))
    assert "password" in result.output.lower() or "settings" in result.output.lower()


# ── CostTracker ───────────────────────────────────────────────────────────────

def test_cost_tracker_multi_agent():
    bus     = TraceEventBus()
    tracker = CostTracker(event_bus=bus)

    tracker.record("support_router", "supervisor",    "gpt-4o-mini", 100, 10, 0.00008)
    tracker.record("support_router", "billing_fast",  "gpt-4o-mini", 300, 80, 0.00030)

    assert tracker.total_cost == pytest.approx(0.00038, abs=1e-6)
    assert "supervisor" in tracker.by_agent()
    assert "billing_fast" in tracker.by_agent()


# ── Pydantic models ───────────────────────────────────────────────────────────

def test_support_request_schema():
    req = SupportRequest(ticket_id="TKT-001", query="My invoice is wrong.")
    assert req.ticket_id == "TKT-001"


def test_support_response_schema():
    resp = SupportResponse(
        ticket_id="TKT-001",
        intent="billing",
        reply="We'll fix that.",
        escalated=False,
        cost_usd=0.00038,
        trace_file="traces/support/TKT-001/abc.jsonl",
    )
    assert not resp.escalated
    assert resp.intent == "billing"
