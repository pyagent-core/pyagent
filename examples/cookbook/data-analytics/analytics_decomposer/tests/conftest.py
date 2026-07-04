"""Test fixtures for analytics_decomposer."""
import pytest
from pyagent_patterns.base import MockLLM


@pytest.fixture()
def all_workers_mocks():
    return MockLLM(responses=[
        '{"assignments": [{"worker": "query", "subtask": "Monthly churn by tier"}, '
        '{"worker": "transform", "subtask": "Cohort by signup month"}, '
        '{"worker": "chart", "subtask": "Line chart per tier"}]}',
        "SELECT plan_tier, COUNT(*) FROM churn_events WHERE ...",
        "JOIN users ON user_id; GROUP BY tenure_bucket, plan_tier.",
        "Small-multiples line chart — one panel per tier.",
        "Churn rose from 3.1% to 4.4%, concentrated in Basic tier < 6 months.",
    ])
