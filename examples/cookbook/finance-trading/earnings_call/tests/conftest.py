"""Earnings Call test fixtures."""
import pytest
from pyagent_patterns.base import MockLLM


@pytest.fixture()
def one_round_mock():
    return MockLLM(responses=[
        "EPS $1.82 vs $1.68 (+8.3%). Revenue $1.24B +14% YoY. "
        "Guidance raised to $4.9–5.0B. Tone: confident. Risk: capex opacity. ANALYSIS COMPLETE",
    ])


@pytest.fixture()
def two_round_mock():
    return MockLLM(responses=[
        "EPS beat. Revenue up. Guidance raised. Tone: measured.",
        "EPS $1.82 vs $1.68 (+8.3%). Revenue $1.24B +14%. Guidance $4.9–5.0B (raised midpoint). "
        "Tone: CEO confident, CFO cautious on capex. Risk: capex opacity → possible FCF miss. ANALYSIS COMPLETE",
    ])
