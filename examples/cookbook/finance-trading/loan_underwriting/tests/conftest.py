"""Loan Underwriting test fixtures."""
import pytest
from pyagent_patterns.base import MockLLM


@pytest.fixture()
def approve_mock():
    return MockLLM(responses=[
        "APPROVE: DTI 38% manageable, score 690 acceptable, growing revenue, equipment collateral.",
        "DECLINE risk: one late payment + thin 2yr history. Propose conditions: personal guarantee.",
        "APPROVE WITH CONDITIONS: DTI manageable, revenue growing. Condition: personal guarantee + annual covenant review.",
    ])


@pytest.fixture()
def decline_mock():
    return MockLLM(responses=[
        "APPROVE case: strong revenue growth, existing collateral.",
        "DECLINE: DTI 38% high for unsecured portion, credit score borderline, thin history.",
        "DECLINE: Repayment risk outweighs growth story at current DTI and thin credit file.",
    ])
