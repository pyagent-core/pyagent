"""Fixtures for tool authorization cookbook tests."""

import pytest
from pyagent_patterns.base import MockLLM


@pytest.fixture
def mock_analyst_llm() -> MockLLM:
    """Mock LLM that first attempts unauthorized vault access, then succeeds with positions."""
    return MockLLM(
        responses=[
            "Thought: I will check credentials in the vault.\nAction: client-vault-reader(ACC-101)\n",
            "Thought: Vault was denied. Now I will read positions.\nAction: portfolio-data.reader(ACC-101)\n",
            "Thought: I have the positions.\nFINISH: Portfolio holds AAPL and MSFT.",
        ]
    )
