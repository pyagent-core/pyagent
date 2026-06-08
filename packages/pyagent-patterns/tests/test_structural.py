"""Tests for Tier 3 structural patterns."""

from __future__ import annotations

import pytest
from pyagent_patterns.base import Agent, MockLLM
from pyagent_patterns.structural import Blackboard, Layered, RoleBased, Topology, TopologyType
from pyagent_patterns.structural.blackboard import BlackboardAgent
from pyagent_patterns.structural.layered import Layer


@pytest.mark.asyncio
async def test_role_based_shared_context():
    ceo_llm = MockLLM(responses=["Strategy: focus on AI"])
    cto_llm = MockLLM(responses=["Architecture: microservices"])

    pattern = RoleBased(
        agents=[Agent("CEO", ceo_llm), Agent("CTO", cto_llm)],
        rounds=1,
        shared_context=True,
    )
    result = await pattern.run("Plan our product")
    assert result.metadata["rounds"] == 1
    assert len(result.messages) == 2


@pytest.mark.asyncio
async def test_layered_multi_layer():
    llm = MockLLM(responses=["Raw data", "Analysis result", "Final synthesis"])

    pattern = Layered(layers=[
        Layer(name="gather", agents=[Agent("gatherer", llm)]),
        Layer(name="analyze", agents=[Agent("analyst", llm)]),
        Layer(name="synthesize", agents=[Agent("synthesizer", llm)]),
    ])
    result = await pattern.run("Analyze the market")
    assert result.metadata["layer_count"] == 3
    assert result.output == "Final synthesis"


@pytest.mark.asyncio
async def test_topology_chain():
    llm = MockLLM(responses=["Step A done", "Step B done", "Step C done"])
    pattern = Topology(
        agents=[Agent("A", llm), Agent("B", llm), Agent("C", llm)],
        topology=TopologyType.CHAIN,
    )
    result = await pattern.run("Process this")
    assert "chain" in result.metadata["topology"]
    assert len(result.messages) == 3


@pytest.mark.asyncio
async def test_topology_star():
    spoke_llm = MockLLM(responses=["Spoke result"])
    hub_llm = MockLLM(responses=["Hub synthesis"])
    pattern = Topology(
        agents=[Agent("Hub", hub_llm), Agent("S1", spoke_llm), Agent("S2", spoke_llm)],
        topology=TopologyType.STAR,
        hub_index=0,
    )
    result = await pattern.run("Analyze this")
    assert result.metadata["topology"] == "star"


@pytest.mark.asyncio
async def test_blackboard_read_write():
    alpha_llm = MockLLM(responses=["alpha_signals: AAPL bullish"])
    risk_llm = MockLLM(responses=["risk_metrics: low volatility"])

    pattern = Blackboard(
        agents=[
            BlackboardAgent(
                agent=Agent("alpha", alpha_llm),
                reads=["task"],
                writes=["alpha_signals"],
            ),
            BlackboardAgent(
                agent=Agent("risk", risk_llm),
                reads=["task", "alpha_signals"],
                writes=["risk_metrics"],
            ),
        ],
        rounds=1,
    )
    result = await pattern.run("Evaluate portfolio")
    assert "final_state" in result.metadata
    assert len(result.messages) == 2
