"""Tests for pyagent-router."""

from __future__ import annotations

import pytest
from pyagent_patterns.base import Agent, MockLLM
from pyagent_router.estimator import CostEstimator
from pyagent_router.middleware import RouterMiddleware
from pyagent_router.scorer import DifficultyScorer
from pyagent_router.selector import Capability, ModelSelector


def test_difficulty_scorer_easy():
    scorer = DifficultyScorer()
    result = scorer.score("What is 2 + 2?")
    assert result.is_easy
    assert result.category == "easy"


def test_difficulty_scorer_hard():
    scorer = DifficultyScorer()
    result = scorer.score(
        "Analyze and compare the trade-offs between microservice and monolithic "
        "architectures. Design an optimal system that synthesizes the benefits of both. "
        "1. Evaluate scalability. 2. Evaluate maintainability. 3. Evaluate cost. "
        "4. Propose a hybrid architecture. 5. Prove its optimality."
    )
    assert result.score >= 4  # Should be medium or hard


def test_cost_estimator_basic():
    estimator = CostEstimator()
    estimate = estimator.estimate("gpt-4o-mini", input_tokens=1000, output_tokens=500)
    assert estimate.model == "gpt-4o-mini"
    assert estimate.input_cost == 1000 * 0.15 / 1_000_000
    assert estimate.output_cost == 500 * 0.60 / 1_000_000
    assert estimate.total_cost == estimate.input_cost + estimate.output_cost


def test_cost_estimator_compare():
    estimator = CostEstimator()
    estimates = estimator.compare("Short text", models=["gpt-4o", "gpt-4o-mini"])
    assert len(estimates) == 2
    assert estimates[0].total_cost <= estimates[1].total_cost  # sorted ascending


def test_model_selector_easy_task():
    selector = ModelSelector()
    result = selector.select("What is the capital of France?")
    # Easy task should select a cheap model
    assert result.difficulty.is_easy or result.difficulty.is_medium
    assert result.model in ["gpt-4.1-nano", "gpt-4o-mini", "gpt-4.1-mini"]


def test_model_selector_with_capability():
    selector = ModelSelector()
    result = selector.select(
        "Write a complex algorithm for graph traversal",
        required_capability=Capability.CODE,
    )
    assert Capability.CODE in [
        cap for spec in selector._specs if spec.name == result.model for cap in spec.capabilities
    ]


@pytest.mark.asyncio
async def test_router_middleware():
    cheap_llm = MockLLM(responses=["Cheap model response"])
    expensive_llm = MockLLM(responses=["Expensive model response"])

    middleware = RouterMiddleware(
        model_registry={"gpt-4o-mini": cheap_llm, "gpt-4o": expensive_llm},
    )
    agent = Agent("test_agent", cheap_llm)
    routed = middleware.wrap(agent)

    from pyagent_patterns.base import Message

    result = await routed.run([Message.user("What is 1+1?")])
    assert result.metadata.get("routed_model") is not None
    assert len(routed.routing_log) == 1
