"""Shared fixtures for campaign planner tests."""
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
def campaign_responses():
    return [
        "Email campaign: 6-email drip. Subject lines A/B tested. CTA: 'Start free trial'.",
        "Social: LinkedIn + Twitter. 3 posts/week. Video testimonial for week 2.",
        "Blog: 2 SEO articles targeting 'best CRM for sales teams'.",
        "Campaign plan: Email (primary), Social (awareness), Blog (SEO). Budget: $20k. Target: 500 signups.",
    ]
