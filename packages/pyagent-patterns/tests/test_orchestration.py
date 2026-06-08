"""Tests for Tier 1 orchestration patterns."""

from __future__ import annotations

import pytest
from pyagent_patterns.base import Agent, MockLLM
from pyagent_patterns.orchestration import (
    FanOutFanIn,
    Hierarchical,
    OrchestratorWorkers,
    Pipeline,
    Supervisor,
)
from pyagent_patterns.orchestration.hierarchical import Team


@pytest.mark.asyncio
async def test_supervisor_routes_correctly():
    classifier_llm = MockLLM(responses=["billing"])
    billing_llm = MockLLM(responses=["Your refund has been processed."])
    tech_llm = MockLLM(responses=["Have you tried restarting?"])

    supervisor = Supervisor(
        classifier=Agent("classifier", classifier_llm),
        routes={
            "billing": Agent("billing_agent", billing_llm),
            "tech": Agent("tech_agent", tech_llm),
        },
    )

    result = await supervisor.run("I need a refund")
    assert result.metadata["route_key"] == "billing"
    assert "refund" in result.output.lower()
    assert result.duration_seconds > 0


@pytest.mark.asyncio
async def test_pipeline_sequential_stages():
    stage_llm = MockLLM(responses=["extracted text", "summarized text", "translated text"])

    pipeline = Pipeline(
        stages=[
            Agent("extract", stage_llm),
            Agent("summarize", stage_llm),
            Agent("translate", stage_llm),
        ]
    )

    result = await pipeline.run("Process this document")
    assert result.metadata["stages"] == 3
    assert len(result.messages) == 3
    assert result.output == "translated text"


@pytest.mark.asyncio
async def test_fanout_parallel_aggregation():
    analyst_llm = MockLLM(responses=["Bullish fundamentals"])
    tech_llm = MockLLM(responses=["RSI oversold"])
    agg_llm = MockLLM(responses=["Combined: BUY signal"])

    fanout = FanOutFanIn(
        agents=[
            Agent("fundamentals", analyst_llm),
            Agent("technicals", tech_llm),
        ],
        aggregator=Agent("aggregator", agg_llm),
    )

    result = await fanout.run("Analyze AAPL")
    assert result.metadata["parallel_agents"] == 2
    assert "BUY" in result.output


@pytest.mark.asyncio
async def test_hierarchical_delegation():
    llm = MockLLM(responses=["Plan decomposed", "Worker output", "Team synthesis", "Final report"])

    teams = [
        Team(
            name="Research",
            lead=Agent("research_lead", llm),
            workers=[Agent("analyst_a", llm)],
        )
    ]

    hierarchical = Hierarchical(manager=Agent("pm", llm), teams=teams)
    result = await hierarchical.run("Build a report")
    assert result.metadata["teams"] == 1
    assert result.metadata["total_workers"] == 1


@pytest.mark.asyncio
async def test_orchestrator_workers_dynamic():
    orch_llm = MockLLM(
        responses=[
            '{"assignments": [{"worker": "researcher", "subtask": "Find data"}]}',
            "Synthesized: research complete",
        ]
    )
    worker_llm = MockLLM(responses=["Data found on topic X"])

    orch = OrchestratorWorkers(
        orchestrator=Agent("orchestrator", orch_llm),
        workers=[Agent("researcher", worker_llm), Agent("writer", worker_llm)],
    )

    result = await orch.run("Write an essay on AI")
    assert result.metadata["workers_used"] == 1
