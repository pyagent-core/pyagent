"""Shared fixtures for literature review tests."""
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
def review_responses():
    return [
        "Found 42 papers on LLM scaling laws from 2020-2024.",
        "Triaged: 28 relevant, 14 excluded (off-topic).",
        "Key findings: compute-optimal scaling outperforms parameter-only scaling.",
        "Citations: Hoffmann et al. 2022 (Chinchilla); Kaplan et al. 2020.",
        "Synthesis: consistent evidence across 6 independent studies.",
        "Literature review complete with 28 sources.",
    ]
