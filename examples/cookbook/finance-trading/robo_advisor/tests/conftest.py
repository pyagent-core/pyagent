"""Robo-Advisor test fixtures."""
import pytest
from pyagent_patterns.base import MockLLM


@pytest.fixture()
def suitable_mock():
    return MockLLM(responses=[
        "Intake: Age 34, SE $145k, $280k investable, retirement at 60, 26yr horizon.",
        "Risk: Aggressive — 26-year horizon, high income, stayed invested through drawdown. Max drawdown: 30%.",
        "SUITABLE — aggressive profile appropriate for age, income, and horizon.",
        "Portfolio: Global Equity 55%, US Small/Mid 15%, Intl Dev 15%, EM 5%, Bonds 10%. IPS: ...",
    ])


@pytest.fixture()
def unsuitable_mock():
    return MockLLM(responses=[
        "Intake: Age 75, retired, $50k income, $200k investable, capital preservation.",
        "Risk: Conservative — age 75, fixed income, low drawdown tolerance. Max drawdown: 5%.",
        "NOT SUITABLE — Aggressive profile would expose retiree to unacceptable drawdown risk.",
        "Portfolio: Short-term bonds 60%, Money market 40%.",
    ])
