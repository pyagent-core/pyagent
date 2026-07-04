"""Wealth Rebalancing test fixtures."""
import pytest
from pyagent_patterns.base import MockLLM


@pytest.fixture()
def compliant_mock():
    return MockLLM(responses=[
        "Mandate: Moderate risk, 8yr horizon, no fossil fuels, max 5% single name.",
        "Market regime: risk-on; equity premium compressed; rates peaked.",
        "Proposed: SPY 35%, AGG 20%, AAPL 5%, MSFT 5%, VEA 20%, cash 15%.",
        "COMPLIANT — all constraints satisfied.",
    ])


@pytest.fixture()
def violation_mock():
    return MockLLM(responses=[
        "Mandate: Moderate risk, no fossil fuels.",
        "Market: neutral.",
        "Proposed: XOM 10%, CVX 8%, SPY 40%, AGG 42%.",
        "VIOLATION: XOM (fossil fuel) and CVX (fossil fuel) breach exclusion constraint.",
    ])
