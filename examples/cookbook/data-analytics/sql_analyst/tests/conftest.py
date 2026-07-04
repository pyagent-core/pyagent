"""Shared fixtures for SQL analyst tests."""
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
def sql_responses():
    return [
        'Action: list_tables\nInput: ""',
        "Observation: orders, customers, regions",
        "Action: run_sql\nInput: SELECT region, SUM(revenue) FROM orders GROUP BY region ORDER BY 2 DESC LIMIT 3",
        "Observation: [(West, 2.1M), (East, 1.8M), (South, 1.2M)]",
        "Final Answer: Top 3 regions by revenue last quarter: West ($2.1M), East ($1.8M), South ($1.2M).",
    ]
