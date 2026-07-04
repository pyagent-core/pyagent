"""Test fixtures for onboarding."""
import pytest
from pyagent_patterns.base import MockLLM


@pytest.fixture()
def onboarding_mocks():
    return MockLLM(responses=[
        "Verification: email confirmed, KYC tier 2, SSO required.",
        "Setup: Pro plan, 50 seats, SSO configured, defaults applied.",
        "FAQ: Billing monthly, 90-day retention, 24h SLAs, docs at docs.example.com.",
        "Success: 30-day check-in scheduled, CSM assigned: bob@vendor.com.",
    ])
