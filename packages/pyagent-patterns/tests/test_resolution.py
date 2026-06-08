"""Tests for Tier 2 resolution patterns."""

from __future__ import annotations

import pytest
from pyagent_patterns.base import Agent, MockLLM
from pyagent_patterns.resolution import (
    CrossReflection,
    Debate,
    EvaluatorOptimizer,
    SelfReflection,
    Voting,
)


@pytest.mark.asyncio
async def test_self_reflection_early_stop():
    llm = MockLLM(responses=["Initial code", "APPROVED"])
    pattern = SelfReflection(agent=Agent("coder", llm), max_rounds=3)
    result = await pattern.run("Write a function")
    assert result.metadata["rounds"] == 1
    assert result.metadata["early_stop"] is True


@pytest.mark.asyncio
async def test_self_reflection_max_rounds():
    llm = MockLLM(
        responses=[
            "Draft 1",
            "Needs work",
            "Draft 2",
            "Still needs work",
            "Draft 3",
            "More feedback",
        ]
    )
    pattern = SelfReflection(agent=Agent("coder", llm), max_rounds=3)
    result = await pattern.run("Write code")
    assert result.metadata["rounds"] == 3


@pytest.mark.asyncio
async def test_cross_reflection():
    gen_llm = MockLLM(responses=["Generated output", "Revised output"])
    rev_llm = MockLLM(responses=["Needs improvement", "APPROVED"])
    pattern = CrossReflection(
        generator=Agent("gen", gen_llm),
        reviewer=Agent("rev", rev_llm),
        max_rounds=3,
    )
    result = await pattern.run("Write an essay")
    assert result.metadata["rounds"] == 2
    assert result.output == "Revised output"


@pytest.mark.asyncio
async def test_debate_multi_round():
    bull_llm = MockLLM(responses=["Bull argument R1", "Bull argument R2"])
    bear_llm = MockLLM(responses=["Bear argument R1", "Bear argument R2"])
    judge_llm = MockLLM(responses=["Decision: BUY based on stronger fundamentals"])

    pattern = Debate(
        debaters=[Agent("bull", bull_llm), Agent("bear", bear_llm)],
        judge=Agent("judge", judge_llm),
        rounds=2,
        positions=["BUY", "SELL"],
    )
    result = await pattern.run("Should we buy AAPL?")
    assert result.metadata["rounds"] == 2
    assert len(result.metadata["debate_log"]) == 4  # 2 debaters × 2 rounds
    assert "BUY" in result.output


@pytest.mark.asyncio
async def test_voting_majority():
    llm_a = MockLLM(responses=["YES\nBecause of X"])
    llm_b = MockLLM(responses=["YES\nBecause of Y"])
    llm_c = MockLLM(responses=["NO\nBecause of Z"])

    pattern = Voting(
        voters=[
            Agent("voter_a", llm_a),
            Agent("voter_b", llm_b),
            Agent("voter_c", llm_c),
        ]
    )
    result = await pattern.run("Is this a good idea?")
    assert result.metadata["winner"] == "YES"
    assert result.metadata["tally"]["YES"] == 2


@pytest.mark.asyncio
async def test_evaluator_optimizer_pass():
    gen_llm = MockLLM(responses=["Great ad copy here"])
    eval_llm = MockLLM(responses=["SCORE: 8\nFEEDBACK: Excellent work"])

    pattern = EvaluatorOptimizer(
        generator=Agent("gen", gen_llm),
        evaluator=Agent("eval", eval_llm),
        pass_threshold=7,
    )
    result = await pattern.run("Write ad copy")
    assert result.metadata["passed"] is True
    assert result.metadata["final_score"] == 8
    assert result.metadata["rounds"] == 1
