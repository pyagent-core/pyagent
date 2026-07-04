"""Test fixtures for contract_review."""
import pytest
from pyagent_patterns.base import MockLLM


@pytest.fixture()
def approved_mocks():
    return MockLLM(responses=[
        "Redline 8.2: Remove 50% termination fee — onerous. Propose 1 month notice only.",
        "APPROVED — redlines are reasonable and proportionate.",
    ])


@pytest.fixture()
def multi_round_mocks():
    return MockLLM(responses=[
        "Redline 8.2: Remove termination fee.",
        "Critique: Add cap on liability too. Revise.",
        "Revised: Remove termination fee + cap liability at 1x fees.",
        "APPROVED — all key risks addressed.",
    ])
