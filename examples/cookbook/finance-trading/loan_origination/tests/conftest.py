"""Loan Origination test fixtures."""
import pytest
from pyagent_patterns.base import MockLLM


@pytest.fixture()
def complete_approve_mock():
    return MockLLM(responses=[
        "Documents: W2 ✓, bank statements ✓, pay stubs ✓, tax returns ✓. All present.",
        "Income verified: $95k/yr. DTI: 32% confirmed. No inconsistencies.",
        "Credit tier: B. Score 740, clean payment history, prior mortgage paid off.",
        "APPROVE: Complete file, solid income, tier B credit, DTI within policy.",
    ])


@pytest.fixture()
def incomplete_refer_mock():
    return MockLLM(responses=[
        "INCOMPLETE: employer verification letter missing. Proceeding with remaining review.",
        "Income: $95k/yr, DTI 32%. Note: self-employment income requires 2-yr average.",
        "Credit tier: B. Score 740.",
        "REFER: INCOMPLETE flag from Stage 1 — employer letter outstanding.",
    ])
