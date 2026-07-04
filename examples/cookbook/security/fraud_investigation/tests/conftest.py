"""Test fixtures for fraud_investigation."""
import pytest
from pyagent_patterns.base import MockLLM


@pytest.fixture()
def high_risk_mocks():
    return MockLLM(responses=[
        "Case file: RISK HIGH. Three wires $9,850 each to Cyprus shell company. Recommend BLOCK.",
    ])


@pytest.fixture()
def low_risk_mocks():
    return MockLLM(responses=[
        "Case file: RISK LOW. Known payee, routine vendor payment. Recommend CLEAR.",
    ])
