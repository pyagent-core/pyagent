"""Tests for Tier 4 advanced patterns."""

from __future__ import annotations

import pytest

from pyagent_patterns.base import Agent, MockLLM
from pyagent_patterns.advanced import HumanInTheLoop, ReAct, Swarm, TalkerReasoner
from pyagent_patterns.advanced.human_in_the_loop import HumanDecision


@pytest.mark.asyncio
async def test_talker_reasoner_fast_path():
    talker_llm = MockLLM(responses=["The weather is sunny today."])
    reasoner_llm = MockLLM(responses=["Deep analysis..."])

    pattern = TalkerReasoner(
        talker=Agent("talker", talker_llm),
        reasoner=Agent("reasoner", reasoner_llm),
    )
    result = await pattern.run("What's the weather?")
    assert result.metadata["system"] == "talker"
    assert result.metadata["escalated"] is False


@pytest.mark.asyncio
async def test_talker_reasoner_escalation():
    talker_llm = MockLLM(responses=["I'm not sure about quantum entanglement."])
    reasoner_llm = MockLLM(responses=["Quantum entanglement is a phenomenon where..."])

    pattern = TalkerReasoner(
        talker=Agent("talker", talker_llm),
        reasoner=Agent("reasoner", reasoner_llm),
    )
    result = await pattern.run("Explain quantum entanglement")
    assert result.metadata["system"] == "reasoner"


@pytest.mark.asyncio
async def test_swarm_basic():
    llm = MockLLM(responses=["Agent view on topic"])
    pattern = Swarm(
        agents=[Agent(f"agent_{i}", llm) for i in range(3)],
        rounds=1,
        neighbor_count=1,
    )
    result = await pattern.run("Discuss the market")
    assert result.metadata["agents"] == 3
    assert result.metadata["rounds"] == 1


@pytest.mark.asyncio
async def test_human_in_the_loop_auto_approve():
    llm = MockLLM(responses=["Generated content"])
    pattern = HumanInTheLoop(agent=Agent("writer", llm))
    result = await pattern.run("Write something")
    assert result.metadata["approved"] is True
    assert result.metadata["revisions"] == 0


@pytest.mark.asyncio
async def test_human_in_the_loop_with_feedback():
    llm = MockLLM(responses=["Draft 1", "Draft 2"])
    call_count = 0

    def review_fn(output, metadata):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return HumanDecision(approved=False, feedback="Add more detail")
        return HumanDecision(approved=True)

    pattern = HumanInTheLoop(agent=Agent("writer", llm), review_fn=review_fn)
    result = await pattern.run("Write something")
    assert result.metadata["approved"] is True
    assert result.metadata["revisions"] == 1


@pytest.mark.asyncio
async def test_react_with_tools():
    responses = [
        "Thought: I need to search\nAction: search(CEO of Apple)",
        "Thought: I found the answer\nFINISH Tim Cook is the CEO of Apple",
    ]
    llm = MockLLM(responses=responses)

    def mock_search(query: str) -> str:
        return "Tim Cook has been CEO of Apple since 2011."

    pattern = ReAct(
        agent=Agent("researcher", llm),
        tools={"search": mock_search},
        max_steps=5,
    )
    result = await pattern.run("Who is the CEO of Apple?")
    assert "Tim Cook" in result.output
    assert result.metadata["steps"] == 2
    assert "search" in result.metadata["tools_used"]
