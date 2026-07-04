"""Test fixtures for log_triage."""
import pytest
from pyagent_patterns.base import MockLLM


@pytest.fixture()
def escalate_mocks():
    return MockLLM(responses=[
        "Asset: vpn-gw-01. Owner: infra-team. Sensitivity: high. Severity: 5.",
        "Confidence 92: matches T1110.003 (password spray) + T1078 (valid accounts). Russian geo.",
        "ESCALATE: impossible travel + MFA failure = likely account takeover.",
    ])


@pytest.fixture()
def false_positive_mocks():
    return MockLLM(responses=[
        "Asset: dev-box. Owner: engineering. Sensitivity: low. Severity: 1.",
        "Confidence 25: matches no known attack patterns. VPN geo change.",
        "FALSE_POSITIVE: VPN provider IP rotation. No MFA failure.",
    ])
