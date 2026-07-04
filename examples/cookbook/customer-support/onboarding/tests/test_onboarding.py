"""Tests for onboarding — MockLLM only."""
from __future__ import annotations
import asyncio
import pytest

from pyagent_patterns.base import Agent, MockLLM
from pyagent_patterns.structural import RoleBased
from pyagent_trace import CostTracker
from pyagent_trace.events import TraceEventBus

from ..agents import ROUNDS
from ..models import OnboardingRequest, OnboardingResponse


def test_role_based_four_roles():
    mock = MockLLM(responses=[
        "Verification: email confirmed.", "Setup: Pro plan, 50 seats.",
        "FAQ: Billing monthly, SLA 24h.", "Success: CSM assigned.",
    ])
    company = RoleBased(agents=[
        Agent("verification",  mock, system_prompt=""),
        Agent("account_setup", mock, system_prompt=""),
        Agent("faq",           mock, system_prompt=""),
        Agent("success",       mock, system_prompt=""),
    ], rounds=1)
    result = asyncio.run(company.run("Acme Corp, 50 seats, Pro plan."))
    assert result is not None


def test_rounds_constant():
    assert ROUNDS == 1


def test_cost_tracker_four_roles():
    bus     = TraceEventBus()
    tracker = CostTracker(event_bus=bus)
    for name in ["verification", "account_setup", "faq", "success"]:
        tracker.record("onboarding", name, "gpt-4o-mini", 100, 50, 0.00008)
    assert tracker.total_cost == pytest.approx(0.00032, abs=1e-6)
    assert len(tracker.by_agent()) == 4


def test_request_schema():
    req = OnboardingRequest(customer_id="CUST-001", customer_info="Acme Corp, Pro plan.")
    assert req.customer_id == "CUST-001"
