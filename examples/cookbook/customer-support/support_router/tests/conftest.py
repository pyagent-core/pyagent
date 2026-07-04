"""Test fixtures for support_router."""
import pytest
from pyagent_patterns.base import MockLLM


@pytest.fixture()
def billing_mocks():
    return MockLLM(responses=["billing", "Your account was charged twice. We'll refund the duplicate."])


@pytest.fixture()
def technical_mocks():
    return MockLLM(responses=["technical", "To reset your password, go to Settings > Security > Reset."])


@pytest.fixture()
def escalate_mocks():
    return MockLLM(responses=["escalate", "Issue escalated to human agent."])
