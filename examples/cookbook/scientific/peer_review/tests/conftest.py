"""Shared fixtures for peer review tests."""
import pytest
from pyagent_patterns.base import MockLLM
from pyagent_trace import CostTracker, Recorder
from pyagent_trace.events import TraceEventBus

SAMPLE_ABSTRACT = "Title: LLM Scaling Laws Revisited. Abstract: We demonstrate compute-optimal training..."


@pytest.fixture
def bus(): return TraceEventBus()

@pytest.fixture
def tracker(bus): return CostTracker(event_bus=bus)

@pytest.fixture
def recorder(bus): return Recorder(event_bus=bus)

@pytest.fixture
def review_responses():
    return [
        "Methodology: Sound experimental design. Control group needed for Experiment 3.",
        "Novelty: Significant advance over Chinchilla. Accept.",
        "Clarity: Well-written. Abstract could be condensed.",
        "Stats reviewer: Effect sizes reported, CI missing for Table 2.",
        "Consensus: Major revision. Add CI in Table 2, add control group.",
    ]
