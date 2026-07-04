"""Test fixtures for cv_screener."""
import pytest
from pyagent_patterns.base import MockLLM


@pytest.fixture()
def strong_hire_mocks():
    return MockLLM(responses=[
        "Skills: 9/10. Python, Kafka, Postgres — all required. Led 40% latency reduction.",
        "Experience: 8/10. 7 years, led 5-person team, built 4k TPS platform.",
        "Collaboration: 8/10. Open-source maintainer, team lead.",
        "Overall: STRONG HIRE. Skills 9, Experience 8, Collaboration 8. Risk: may be overqualified.",
    ])


@pytest.fixture()
def no_hire_mocks():
    return MockLLM(responses=[
        "Skills: 3/10. No Python or distributed systems experience.",
        "Experience: 4/10. 2 years, no leadership.",
        "Collaboration: 5/10. Solo projects only.",
        "Overall: NO HIRE. Scores too low on required skills.",
    ])
