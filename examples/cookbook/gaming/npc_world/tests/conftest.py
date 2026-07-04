"""Shared fixtures for NPC world tests."""
import pytest
from pyagent_patterns.base import MockLLM
from pyagent_trace import CostTracker, Recorder
from pyagent_trace.events import TraceEventBus

DEMO_STATE = "Forest world. Resources: 10 wood, 5 stone. Population: 3."


@pytest.fixture
def bus(): return TraceEventBus()

@pytest.fixture
def tracker(bus): return CostTracker(event_bus=bus)

@pytest.fixture
def recorder(bus): return Recorder(event_bus=bus)

@pytest.fixture
def world_responses():
    return [
        "Explorer: Discovered river to the north. New map: forest + river.",
        "Builder: Built lumber mill using 5 wood. Resources: 5 wood, 5 stone, +3 wood/turn.",
        "Trader: Established trade route with nearby village. Economy: active.",
        "Chronicler: Day 1 — the settlers discovered a river and built their first mill.",
    ]
