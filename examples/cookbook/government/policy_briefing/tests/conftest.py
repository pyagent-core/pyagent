"""Shared fixtures for policy briefing tests."""
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
def briefing_responses():
    return [
        "Macro analysis: carbon tax at $50/tonne reduces GDP by 0.3% but creates 80k green jobs.",
        "Impact model: 15% emissions reduction by 2030, $4B annual revenue.",
        "Constitutional review: within federal powers under Commerce Clause.",
        "Precedent: BC carbon tax (2008) upheld, EU ETS sustained.",
        "Economics synthesis: net positive with targeted rebates for low-income households.",
        "Policy briefing: Recommend PASSAGE with income-adjusted rebate program.",
    ]
