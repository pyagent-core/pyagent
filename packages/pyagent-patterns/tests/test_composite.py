"""Tests for composite patterns."""

from __future__ import annotations

import pytest
from pyagent_patterns.base import Agent, MockLLM
from pyagent_patterns.composite import CompositePattern, min_length_check
from pyagent_patterns.resolution import SelfReflection, Voting


@pytest.mark.asyncio
async def test_composite_first_pattern_passes():
    llm = MockLLM(responses=["Good output that is long enough to pass the check", "APPROVED"])
    reflection = SelfReflection(agent=Agent("coder", llm), max_rounds=1)
    voting_llm = MockLLM(responses=["YES", "YES"])
    voting = Voting(voters=[Agent("a", voting_llm), Agent("b", voting_llm)])

    composite = CompositePattern(
        patterns=[reflection, voting],
        quality_check=min_length_check(10),
    )
    result = await composite.run("Do something")
    assert result.metadata["escalation_level"] == 0
    assert result.metadata["total_patterns_tried"] == 1


@pytest.mark.asyncio
async def test_composite_escalation():
    # First pattern produces too-short output
    short_llm = MockLLM(responses=["Short", "APPROVED"])
    reflection = SelfReflection(agent=Agent("coder", short_llm), max_rounds=1)

    # Second pattern produces adequate output
    vote_llm = MockLLM(responses=[
        "A much longer and more detailed response that passes the length check",
        "A much longer and more detailed response that passes the length check",
    ])
    voting = Voting(voters=[Agent("a", vote_llm), Agent("b", vote_llm)])

    composite = CompositePattern(
        patterns=[reflection, voting],
        quality_check=min_length_check(30),
    )
    result = await composite.run("Do something complex")
    assert result.metadata["escalation_level"] == 1
    assert result.metadata["total_patterns_tried"] == 2
