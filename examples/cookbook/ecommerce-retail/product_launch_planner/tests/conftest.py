"""Shared fixtures for product launch planner tests."""
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
def launch_responses():
    return [
        "Pricing strategy: $129 launch price, $149 MSRP. Competitive vs Keychron K2.",
        "Copy: 'Code faster. Type quieter.' — headline. 3 key benefits listed.",
        "SEO: keywords — mechanical keyboard developer, wireless coding keyboard.",
        "Inventory: 500 units pre-built, reorder at 100 units.",
        "Launch plan synthesized: price $129, 3 channels, 500 units stocked.",
    ]
