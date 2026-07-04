"""Shared pytest fixtures for all cookbook recipe tests."""
from __future__ import annotations
import asyncio
import os
import pytest
from pyagent_patterns.base import MockLLM


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture()
def mock_env(monkeypatch):
    """Patch all external env vars so tests run without real credentials."""
    env = {
        "ANTHROPIC_API_KEY": "test-anthropic-key",
        "OPENAI_API_KEY": "test-openai-key",
        "GEMINI_API_KEY": "test-gemini-key",
        "COMPLIANCE_API_URL": "https://compliance.test",
        "COMPLIANCE_API_KEY": "test-compliance-key",
        "PAGERDUTY_ROUTING_KEY": "test-pd-routing",
        "PAGERDUTY_API_KEY": "test-pd-api",
        "ZENDESK_URL": "https://test.zendesk.com",
        "ZENDESK_EMAIL": "agent@test.com",
        "ZENDESK_TOKEN": "test-zendesk-token",
        "REVIEW_QUEUE_URL": "https://reviews.test",
        "REVIEW_QUEUE_TOKEN": "test-review-token",
        "ESG_DATA_API_URL": "https://esg.test",
        "ESG_DATA_API_KEY": "test-esg-key",
        "LOS_API_URL": "https://los.test",
        "LOS_API_KEY": "test-los-key",
        "CREDIT_BUREAU_URL": "https://credit.test",
        "CREDIT_BUREAU_KEY": "test-credit-key",
    }
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    return env


def make_mock_llm(*responses: str) -> MockLLM:
    """Factory for a MockLLM with the given ordered responses."""
    return MockLLM(responses=list(responses))
