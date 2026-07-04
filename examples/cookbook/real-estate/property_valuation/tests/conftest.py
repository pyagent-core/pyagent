"""Shared fixtures for property valuation tests."""
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
def valuation_responses():
    return [
        "Data: 3BR/2BA, 1850sqft, Austin 78704. Last sale: $420k (2021).",
        "Comps: 5 nearby sales 2023-2024. Range: $485k-$530k. Median: $510k.",
        "Market analysis: Austin 78704 up 6% YoY. Strong demand from tech sector.",
        "Narrative: 3BR/2BA in prime South Austin. Estimated value: $505,000-$520,000.",
        "QA passed: estimate within 2% of comp median. Confidence: HIGH.",
    ]
