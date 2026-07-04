"""Test fixtures for portfolio_review."""
import pytest
from pyagent_patterns.base import MockLLM


@pytest.fixture()
def equity_mocks():
    return MockLLM(responses=[
        "equity",
        "AAPL: strong moat, PE 28x fair, catalyst: Vision Pro super-cycle.",
        "Recommendation: HOLD with positive bias. Score: 8/10.",
    ])


@pytest.fixture()
def bond_mocks():
    return MockLLM(responses=[
        "fixed_income",
        "10Y UST: duration 8.7y, AA+, rate sensitivity high amid Fed pivot.",
        "Recommendation: REDUCE duration. Score: 7/10.",
    ])


@pytest.fixture()
def low_score_then_high():
    return MockLLM(responses=[
        "equity",
        "Stock is fine.",
        "Score: 4/10. Missing explicit downside and position sizing.",
        "Stock is fine. Downside: -20% if earnings miss. Position: 8% cap.",
        "Score: 9/10. All criteria met.",
    ])
