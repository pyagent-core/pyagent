"""Shared fixtures for essay grader tests."""
import pytest
from pyagent_patterns.base import MockLLM
from pyagent_trace import CostTracker, Recorder
from pyagent_trace.events import TraceEventBus

SAMPLE_ESSAY = "Title: The Role of AI in Education\n\nAI tools are transforming learning by personalizing content..."


@pytest.fixture
def bus(): return TraceEventBus()

@pytest.fixture
def tracker(bus): return CostTracker(event_bus=bus)

@pytest.fixture
def recorder(bus): return Recorder(event_bus=bus)

@pytest.fixture
def grade_a_responses():
    return [
        "Grade: A. Strong thesis, excellent evidence, clear structure. Score: 92/100.",
        "Grade: A. Compelling argument, well-sourced. Score: 91/100.",
        "Grade: A. Sophisticated language, logical flow. Score: 90/100.",
    ]

@pytest.fixture
def grade_c_responses():
    return [
        "Grade: C. Weak thesis, missing evidence. Score: 72/100.",
        "Grade: C. Unclear argument, some grammar issues. Score: 70/100.",
        "Grade: B. Decent structure but thin analysis. Score: 78/100.",
    ]
