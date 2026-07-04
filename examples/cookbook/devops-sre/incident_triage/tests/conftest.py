"""Test fixtures for incident_triage."""
import pytest
from pyagent_patterns.base import MockLLM


@pytest.fixture()
def non_prod_mocks():
    return MockLLM(responses=[
        "payments-svc: 5xx since 14 min ago, connection pool at 100/100.",
        "Root cause: connection pool exhausted after deploy — likely missing pool size tuning.",
        "TOUCHES_PROD: no\nRestart payments-svc replica in staging to verify fix.",
    ])


@pytest.fixture()
def prod_mocks():
    return MockLLM(responses=[
        "checkout: 5xx rate 12%, db connections maxed.",
        "Root cause: DB connection leak in new deploy.",
        "TOUCHES_PROD: yes\nRollback payments-svc to v1.2.3.",
    ])
