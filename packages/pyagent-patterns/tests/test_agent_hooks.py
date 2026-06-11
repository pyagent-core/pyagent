"""Tests for Agent hook-based integration (trace, context, compression, cost)."""

from __future__ import annotations

import pytest
from pyagent_patterns.base import Agent, MockLLM, Message


@pytest.mark.asyncio
async def test_agent_run_without_hooks():
    """Backward compat: Agent.run works identically when no hooks are wired."""
    llm = MockLLM(responses=["Hello!"])
    agent = Agent("greeter", llm, system_prompt="Be friendly.")
    result = await agent.run([Message.user("Hi")])
    assert result.content == "Hello!"
    assert result.name == "greeter"


@pytest.mark.asyncio
async def test_agent_trace_hook_emits_events():
    """Agent emits agent_start and agent_end trace events when trace_bus is set."""
    from pyagent_trace.events import TraceEventBus

    bus = TraceEventBus()
    events = []
    bus.subscribe(lambda e: events.append(e))

    llm = MockLLM(responses=["result"])
    agent = Agent("analyst", llm)
    agent.set_trace_bus(bus)

    await agent.run([Message.user("analyse this")])

    event_types = [e.event_type for e in events]
    assert "agent_start" in event_types
    assert "agent_end" in event_types

    end_event = next(e for e in events if e.event_type == "agent_end")
    assert end_event.agent_name == "analyst"
    assert "duration_seconds" in end_event.payload
    assert "output_tokens" in end_event.payload


@pytest.mark.asyncio
async def test_agent_context_hook_reads_and_writes():
    """Agent reads context before LLM call and writes output after."""
    from pyagent_context import ContextLedger
    from pyagent_context.item import ContextItem, TrustLevel

    ledger = ContextLedger()
    ledger.add("Prior knowledge: revenue was $10B", source="database", trust_level=TrustLevel.VERIFIED)

    llm = MockLLM(responses=["Analysis complete"])
    agent = Agent("analyst", llm)
    agent.set_context(ledger)

    await agent.run([Message.user("Analyse revenue")])

    # Agent should have written its output to the ledger
    assert len(ledger) == 2
    last_item = ledger.items[-1]
    assert last_item.source == "analyst"
    assert last_item.content == "Analysis complete"
    assert last_item.trust_level == TrustLevel.INFERRED

    # LLM should have received context messages prepended
    assert llm.call_count == 1
    call_messages = llm.call_log[0]
    # First should be system prompt (if any) or context, then user message
    contents = [m.content for m in call_messages]
    assert any("revenue was $10B" in c for c in contents)


@pytest.mark.asyncio
async def test_agent_compressor_hook():
    """Agent compresses output when compressor is set."""
    from pyagent_compress import MessageCompressor

    # Use a long response that can be compressed
    long_response = (
        "Let me think about this carefully. "
        "The data shows a significant increase of 25% in revenue. "
        "This is primarily driven by the new product launch in Q3. "
        "In conclusion, the company is performing well above expectations. "
        "I believe the trend will continue into next quarter."
    )
    llm = MockLLM(responses=[long_response])
    agent = Agent("analyst", llm)
    agent.set_compressor(MessageCompressor(target_ratio=0.5))

    result = await agent.run([Message.user("Analyse")])

    # Output should be compressed (shorter than original)
    assert len(result.content) <= len(long_response)
    assert result.metadata.get("compressed") is True
    assert "savings_pct" in result.metadata


@pytest.mark.asyncio
async def test_agent_cost_tracker_hook():
    """Agent records cost when cost_tracker is set."""
    from pyagent_trace import CostTracker

    tracker = CostTracker()
    llm = MockLLM(responses=["done"])
    agent = Agent("worker", llm)
    agent.set_cost_tracker(tracker)

    await agent.run([Message.user("Do work")])

    assert len(tracker._entries) == 1
    entry = tracker._entries[0]
    assert entry.agent_name == "worker"
    assert entry.input_tokens > 0
    assert entry.output_tokens > 0


@pytest.mark.asyncio
async def test_agent_hook_chaining():
    """Setter methods return self for chaining."""
    from pyagent_trace.events import TraceEventBus
    from pyagent_trace import CostTracker

    llm = MockLLM(responses=["ok"])
    bus = TraceEventBus()

    agent = (
        Agent("chained", llm)
        .set_trace_bus(bus)
        .set_cost_tracker(CostTracker())
    )

    assert agent._trace_bus is bus
    assert agent._cost_tracker is not None
    assert agent.name == "chained"


@pytest.mark.asyncio
async def test_agent_all_hooks_together():
    """All hooks work simultaneously without interference."""
    from pyagent_trace.events import TraceEventBus
    from pyagent_trace import CostTracker
    from pyagent_context import ContextLedger
    from pyagent_compress import MessageCompressor

    bus = TraceEventBus()
    events = []
    bus.subscribe(lambda e: events.append(e))

    ledger = ContextLedger()
    tracker = CostTracker(event_bus=bus)
    compressor = MessageCompressor(target_ratio=0.5)

    long_response = (
        "The analysis reveals important findings. "
        "Revenue increased by 30% year-over-year, reaching $50 billion. "
        "This growth was driven by strong performance in cloud services. "
        "In my opinion, the outlook remains positive for the next fiscal year."
    )
    llm = MockLLM(responses=[long_response])

    agent = (
        Agent("analyst", llm)
        .set_trace_bus(bus)
        .set_context(ledger)
        .set_compressor(compressor)
        .set_cost_tracker(tracker)
    )

    result = await agent.run([Message.user("Full analysis")])

    # Trace events emitted
    event_types = {e.event_type for e in events}
    assert "agent_start" in event_types
    assert "agent_end" in event_types

    # Context written
    assert len(ledger) >= 1

    # Cost recorded (both from agent and from CostTracker via bus)
    assert tracker.total_tokens > 0

    # Result is valid
    assert result.content
    assert result.name == "analyst"
