"""Tests for Pattern hook-based integration (trace_bus on Pattern.run)."""

from __future__ import annotations

import pytest
from pyagent_patterns.base import Agent, MockLLM, Message
from pyagent_patterns.orchestration import Pipeline


@pytest.mark.asyncio
async def test_pattern_run_without_hooks():
    """Backward compat: Pattern.run works identically when no hooks are wired."""
    llm = MockLLM(responses=["step1", "step2"])
    pipeline = Pipeline(stages=[
        Agent("a", llm),
        Agent("b", llm),
    ])
    result = await pipeline.run("test task")
    assert result.output
    assert result.metadata["pattern_type"] == "pipeline"


@pytest.mark.asyncio
async def test_pattern_trace_hook_emits_events():
    """Pattern emits pattern_start and pattern_end trace events."""
    from pyagent_trace.events import TraceEventBus

    bus = TraceEventBus()
    events = []
    bus.subscribe(lambda e: events.append(e))

    llm = MockLLM(responses=["output"])
    pipeline = Pipeline(stages=[Agent("a", llm)])
    pipeline.set_trace_bus(bus)

    result = await pipeline.run("test")

    event_types = [e.event_type for e in events]
    assert "pattern_start" in event_types
    assert "pattern_end" in event_types

    start = next(e for e in events if e.event_type == "pattern_start")
    assert start.pattern_type == "pipeline"

    end = next(e for e in events if e.event_type == "pattern_end")
    assert "duration_seconds" in end.payload
    assert "token_estimate" in end.payload
    assert "output_length" in end.payload


@pytest.mark.asyncio
async def test_pattern_trace_never_breaks_execution():
    """Even if trace_bus raises, pattern execution completes normally."""

    class BrokenBus:
        def emit(self, event):
            raise RuntimeError("bus broken!")

    llm = MockLLM(responses=["output"])
    pipeline = Pipeline(stages=[Agent("a", llm)])
    pipeline._trace_bus = BrokenBus()

    # Should not raise
    result = await pipeline.run("test")
    assert result.output == "output"
