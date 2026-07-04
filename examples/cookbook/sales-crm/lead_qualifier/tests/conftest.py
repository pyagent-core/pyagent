"""Shared fixtures for lead qualifier tests."""
import pytest
from pyagent_patterns.base import MockLLM
from pyagent_trace import CostTracker, Recorder
from pyagent_trace.events import TraceEventBus


@pytest.fixture
def bus(): return TraceEventBus()

@pytest.fixture
def tracker(bus): return CostTracker(event_bus=bus)

@pytest.fixture
def recorder(bus): return Recorder(event_bus=bus)

@pytest.fixture
def hot_lead_responses():
    return [
        "Lead score: 92/100 — HOT. Budget confirmed, decision maker engaged, Q3 timeline.",
        "Account exec: Scheduled demo for Thursday. Sent pricing proposal.",
    ]

@pytest.fixture
def cold_lead_responses():
    return [
        "Lead score: 18/100 — COLD. No budget, no decision maker, vague timeline.",
        "Cold hold: Added to newsletter. Follow up in 6 months.",
    ]
