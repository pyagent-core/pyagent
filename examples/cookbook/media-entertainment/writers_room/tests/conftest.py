"""Shared fixtures for writers' room tests."""
import pytest
from pyagent_patterns.base import MockLLM
from pyagent_trace import CostTracker, Recorder
from pyagent_trace.events import TraceEventBus

ROUNDS = 2


@pytest.fixture
def bus(): return TraceEventBus()

@pytest.fixture
def tracker(bus): return CostTracker(event_bus=bus)

@pytest.fixture
def recorder(bus): return Recorder(event_bus=bus)

@pytest.fixture
def room_responses():
    return [
        "Showrunner: Strong concept. The power outage reveals character relationships.",
        "Staff writer: Opening scene: vault door closes, lights go out. Tension builds.",
        "Script editor: Dialogue tight. Add comedic beat before act break.",
        "Continuity: Check timeline — heist takes 90 mins, not 2 hours.",
        "Network exec: Approved. Greenlight with note: raise stakes in act 3.",
        "Showrunner [r2]: Revised. Act 3 twist: inside job. Network note addressed.",
    ]
