"""Shared fixtures for trip planner tests."""
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
def trip_responses():
    return [
        "Flights: SFO→NRT, April 2. JAL direct, $850pp. Return April 12.",
        "Lodging: Mix of ryokans and business hotels. 5 nights Tokyo, 3 Kyoto, 2 Osaka. ~$120/night avg.",
        "Activities: Tsukiji breakfast, Arashiyama bamboo, Osaka food tour, Fushimi Inari hike.",
        "Budget: Flights $1,700, lodging $1,200, food $600, activities $400, misc $100. Total: $4,000. Under $6k budget.",
        "Local guide: April cherry blossom peak in Tokyo April 5-10. Book Shinjuku Gyoen tickets in advance.",
        "10-day Japan itinerary complete. Total: $4,000. Highlights: cherry blossoms, ryokans, food tours.",
    ]
