"""Shared fixtures for compliance checker tests."""
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
def compliant_responses():
    return [
        "All obligations identified: data retention 7 years, breach notification 72h.",
        "Scope: applies to EU residents' PII.",
        "Controls mapped: AES-256 encryption meets requirement R-01.",
        "Policy: data-classification-v2.pdf covers clause 4.1.",
        "Evidence: last audit 2024-01. All controls verified.",
        "COMPLIANT. All 5 obligations satisfied with documented controls.",
    ]

@pytest.fixture
def non_compliant_responses():
    return [
        "Obligations identified: breach notification 72h, right to erasure.",
        "Scope: applies to all user records.",
        "Controls gap: right to erasure workflow missing.",
        "Policy gap: no documented erasure procedure.",
        "Evidence: no erasure tests found.",
        "NON-COMPLIANT. Missing: erasure workflow (R-03), policy documentation.",
    ]
