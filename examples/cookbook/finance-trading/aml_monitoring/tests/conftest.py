"""AML Monitoring test fixtures."""
import pytest
from pyagent_patterns.base import MockLLM


@pytest.fixture()
def low_risk_mock():
    return MockLLM(responses=[
        "Flags: NONE.",
        "Risk: 15 — Low. Drivers: known recurring vendor, domestic transfer.",
        "ACME Corp: established vendor, 5-year relationship, US-based.",
    ])


@pytest.fixture()
def high_risk_mock():
    return MockLLM(responses=[
        "Flags: structuring ($9,850 ×3), high-risk jurisdiction (Cyprus), velocity breach.",
        "Risk: 88 — High. Drivers: structuring pattern + new counterparty in high-risk jurisdiction.",
        "ACME Consulting Ltd: registered 30 days ago, no known business activity, Cyprus (FATF grey-listed).",
        "SAR narrative: Subject ACC-7731 conducted three wire transfers totalling $29,550 to ACME Consulting...",
    ])
