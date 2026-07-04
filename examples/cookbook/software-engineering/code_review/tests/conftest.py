"""Test fixtures for code_review."""
import pytest
from pyagent_patterns.base import MockLLM


@pytest.fixture()
def approved_mocks():
    return MockLLM(responses=[
        "The code looks good. Consider adding input validation.",
        "APPROVED — implementation is clear and maintainable.",
        "Security score: 9/10. No vulnerabilities found.",
    ])


@pytest.fixture()
def security_fail_mocks():
    return MockLLM(responses=[
        "The SQL query is built with string formatting — injection risk.",
        "APPROVED — after review.",
        "Security score: 3/10. SQL injection vulnerability on line 3.",
    ])
