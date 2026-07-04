"""Test fixtures for startup_simulation."""
import pytest
from pyagent_patterns.base import MockLLM


@pytest.fixture()
def full_company_mocks():
    return MockLLM(responses=[
        "PRD: standup-cli summarizes git commits into weekly notes. Users: dev teams.",
        "Design: git-log parser + LLM summarizer. Stack: Python + Click.",
        "Code skeleton: collect.py / group.py / summarize.py.",
        "Tests: empty repo, huge diffs, merge commits.",
        "Round 2 PRD: refined scope.",
        "Round 2 Design: edge cases handled.",
        "Round 2 Code: function signatures finalized.",
        "Round 2 QA: acceptance criteria per story.",
    ])
