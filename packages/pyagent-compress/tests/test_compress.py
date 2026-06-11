"""Tests for pyagent-compress."""

from __future__ import annotations

import pytest
from pyagent_compress.budget import BudgetExceededError, TokenBudget
from pyagent_compress.compressor import MessageCompressor
from pyagent_compress.middleware import CompressMiddleware
from pyagent_compress.pruner import AgentPruner, InteractionPruner
from pyagent_patterns.base import Agent, Message, MockLLM, Role


def test_compressor_reduces_tokens():
    compressor = MessageCompressor(target_ratio=0.5)
    text = (
        "Let me think about this carefully. Basically, the analysis shows that "
        "revenue increased by 15% year-over-year. The data indicates a strong "
        "upward trend in Q3 earnings. In other words, the company is performing "
        "well above market expectations. It's worth noting that the profit margin "
        "expanded to 23%, which is significant compared to the industry average of 18%. "
        "The conclusion is that this represents a solid buy opportunity."
    )
    result = compressor.compress(text)
    assert result.compressed_tokens < result.original_tokens
    assert result.savings_pct > 0


def test_compressor_short_text_unchanged():
    compressor = MessageCompressor()
    result = compressor.compress("Short text")
    assert result.compressed == result.original


def test_agent_pruner_scores():
    pruner = AgentPruner(min_contribution=0.3)
    messages = [
        Message(role=Role.ASSISTANT, content="Unique analysis of market trends", name="analyst"),
        Message(role=Role.ASSISTANT, content="Unique analysis of market trends", name="copycat"),
        Message(
            role=Role.ASSISTANT, content="Different risk assessment with new data", name="risk"
        ),
    ]
    scores = pruner.score_agents(messages, "analyze market trends")
    assert len(scores) == 3


def test_interaction_pruner_consensus():
    pruner = InteractionPruner(consensus_threshold=0.5, min_rounds=1)

    # Same outputs → consensus
    assert pruner.has_consensus(["The answer is 42", "The answer is 42"], current_round=1) is True

    # Very different outputs → no consensus
    assert (
        pruner.has_consensus(
            [
                "Completely different analysis about stocks",
                "An unrelated discussion about weather patterns",
            ],
            current_round=1,
        )
        is False
    )


def test_interaction_pruner_min_rounds():
    pruner = InteractionPruner(consensus_threshold=0.5, min_rounds=2)
    # Round 1: should not trigger even if consensus
    assert pruner.has_consensus(["Same", "Same"], current_round=1) is False
    # Round 2: now can trigger
    assert pruner.has_consensus(["Same answer", "Same answer"], current_round=2) is True


def test_token_budget_tracking():
    budget = TokenBudget(workflow_limit=10000, per_agent_limit=5000, strict=False)
    budget.consume("agent_a", 1000)
    budget.consume("agent_b", 2000)
    assert budget.total_used == 3000
    assert budget.remaining() == 7000
    assert budget.remaining("agent_a") == 4000


def test_token_budget_strict_raises():
    budget = TokenBudget(workflow_limit=100, per_agent_limit=50, strict=True)
    budget.consume("agent_a", 40)
    with pytest.raises(BudgetExceededError):
        budget.consume("agent_a", 20)  # Exceeds per-agent limit of 50


@pytest.mark.asyncio
async def test_compress_middleware():
    llm = MockLLM(
        responses=[
            "Let me think about this carefully. Basically, the revenue data shows "
            "a 15% increase year-over-year, which is significant. The profit margin "
            "expanded to 23%. In conclusion, this is a buy signal."
        ]
    )
    agent = Agent("analyst", llm)

    middleware = CompressMiddleware(target_ratio=0.5)
    compressed = middleware.wrap(agent)

    result = await compressed.run([Message.user("Analyze AAPL")])
    assert result.metadata.get("compressed") is True
    assert result.metadata.get("savings_pct", 0) >= 0
