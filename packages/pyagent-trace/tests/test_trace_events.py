"""Tests for TraceEventBus and producer wiring (Recorder, CostTracker)."""

from __future__ import annotations

import asyncio
import time

import pytest
from pyagent_patterns.base import Message, Role
from pyagent_trace.events import TraceEvent, TraceEventBus


# --- TraceEvent dataclass ---


def test_trace_event_dataclass_frozen():
    """TraceEvent is immutable."""
    event = TraceEvent(timestamp=1.0, event_type="llm_call")
    with pytest.raises(AttributeError):
        event.event_type = "other"  # type: ignore[misc]


def test_trace_event_all_fields():
    """All fields are populated correctly."""
    payload = {"model": "gpt-4o", "tokens": 500}
    event = TraceEvent(
        timestamp=123.456,
        event_type="llm_call",
        agent_name="analyst",
        pattern_type="pipeline",
        payload=payload,
    )
    assert event.timestamp == 123.456
    assert event.event_type == "llm_call"
    assert event.agent_name == "analyst"
    assert event.pattern_type == "pipeline"
    assert event.payload == payload


def test_trace_event_defaults():
    """Default values for optional fields."""
    event = TraceEvent(timestamp=1.0, event_type="test")
    assert event.agent_name == ""
    assert event.pattern_type == ""
    assert event.payload == {}


# --- TraceEventBus ---


def test_bus_subscribe_and_emit():
    """Subscriber receives emitted events."""
    bus = TraceEventBus()
    received: list[TraceEvent] = []
    bus.subscribe(received.append)

    event = TraceEvent(timestamp=time.time(), event_type="llm_call", agent_name="a1")
    bus.emit(event)

    assert len(received) == 1
    assert received[0] is event


def test_bus_subscribe_filter():
    """Filtered subscriber only gets matching event_types."""
    bus = TraceEventBus()
    received: list[TraceEvent] = []
    bus.subscribe_filter({"llm_call"}, received.append)

    bus.emit(TraceEvent(timestamp=1.0, event_type="llm_call"))
    bus.emit(TraceEvent(timestamp=2.0, event_type="pattern_start"))
    bus.emit(TraceEvent(timestamp=3.0, event_type="llm_call"))

    assert len(received) == 2
    assert all(e.event_type == "llm_call" for e in received)


def test_bus_unsubscribe():
    """Unsubscribed callback stops receiving."""
    bus = TraceEventBus()
    received: list[TraceEvent] = []
    sub_id = bus.subscribe(received.append)

    bus.emit(TraceEvent(timestamp=1.0, event_type="test"))
    assert len(received) == 1

    bus.unsubscribe(sub_id)
    bus.emit(TraceEvent(timestamp=2.0, event_type="test"))
    assert len(received) == 1  # no new events


def test_bus_unsubscribe_filtered():
    """Unsubscribed filtered callback stops receiving."""
    bus = TraceEventBus()
    received: list[TraceEvent] = []
    sub_id = bus.subscribe_filter({"test"}, received.append)

    bus.emit(TraceEvent(timestamp=1.0, event_type="test"))
    assert len(received) == 1

    bus.unsubscribe(sub_id)
    bus.emit(TraceEvent(timestamp=2.0, event_type="test"))
    assert len(received) == 1


def test_bus_unsubscribe_nonexistent():
    """Unsubscribing a nonexistent ID is a no-op."""
    bus = TraceEventBus()
    bus.unsubscribe("nonexistent")  # should not raise


def test_bus_multiple_subscribers():
    """Fan-out to N subscribers."""
    bus = TraceEventBus()
    r1: list[TraceEvent] = []
    r2: list[TraceEvent] = []
    r3: list[TraceEvent] = []
    bus.subscribe(r1.append)
    bus.subscribe(r2.append)
    bus.subscribe_filter({"llm_call"}, r3.append)

    bus.emit(TraceEvent(timestamp=1.0, event_type="llm_call"))

    assert len(r1) == 1
    assert len(r2) == 1
    assert len(r3) == 1


def test_bus_emit_async():
    """Async emit works with sync callbacks."""
    bus = TraceEventBus()
    received: list[TraceEvent] = []
    bus.subscribe(received.append)

    event = TraceEvent(timestamp=1.0, event_type="test")
    asyncio.run(bus.emit_async(event))

    assert len(received) == 1
    assert received[0] is event


def test_bus_emit_async_filtered():
    """Async emit works with filtered subscribers."""
    bus = TraceEventBus()
    received: list[TraceEvent] = []
    bus.subscribe_filter({"test"}, received.append)

    asyncio.run(bus.emit_async(TraceEvent(timestamp=1.0, event_type="test")))
    asyncio.run(bus.emit_async(TraceEvent(timestamp=2.0, event_type="other")))

    assert len(received) == 1


def test_bus_emit_no_subscribers():
    """No error when no subscribers."""
    bus = TraceEventBus()
    bus.emit(TraceEvent(timestamp=1.0, event_type="test"))  # should not raise


# --- Recorder → bus wiring ---


def test_recorder_emits_pattern_start():
    """Recorder.start() emits pattern_start to bus."""
    from pyagent_trace.recorder import Recorder

    bus = TraceEventBus()
    received: list[TraceEvent] = []
    bus.subscribe(received.append)

    rec = Recorder(event_bus=bus)
    rec.start("debate")

    assert len(received) == 1
    assert received[0].event_type == "pattern_start"
    assert received[0].pattern_type == "debate"


def test_recorder_emits_llm_call():
    """Recorder.record_llm_call() emits llm_call to bus."""
    from pyagent_trace.recorder import Recorder

    bus = TraceEventBus()
    received: list[TraceEvent] = []
    bus.subscribe(received.append)

    rec = Recorder(event_bus=bus)
    rec.start("pipeline")
    rec.record_llm_call(
        "agent1",
        [Message(role=Role.USER, content="Hello")],
        "Response",
        metadata={"model": "gpt-4o"},
    )

    # received: [pattern_start, llm_call]
    assert len(received) == 2
    llm_event = received[1]
    assert llm_event.event_type == "llm_call"
    assert llm_event.agent_name == "agent1"
    assert llm_event.payload["model"] == "gpt-4o"
    assert llm_event.payload["response"] == "Response"


def test_recorder_emits_pattern_end():
    """Recorder.end() emits pattern_end to bus."""
    from pyagent_trace.recorder import Recorder

    bus = TraceEventBus()
    received: list[TraceEvent] = []
    bus.subscribe(received.append)

    rec = Recorder(event_bus=bus)
    rec.start("debate")
    rec.end("Final output")

    assert len(received) == 2
    end_event = received[1]
    assert end_event.event_type == "pattern_end"
    assert end_event.payload["result_output"] == "Final output"
    assert "duration_seconds" in end_event.payload


def test_recorder_no_bus_still_works():
    """Recorder without bus still records to entries (backward compat)."""
    from pyagent_trace.recorder import Recorder

    rec = Recorder()  # no bus
    rec.start("debate")
    rec.record_llm_call(
        "agent1",
        [Message(role=Role.USER, content="Hello")],
        "Response",
    )
    rec.end("done")

    assert len(rec.entries) == 3
    assert rec.entries[0].event_type == "pattern_start"
    assert rec.entries[1].event_type == "llm_call"
    assert rec.entries[2].event_type == "pattern_end"


# --- CostTracker → bus wiring ---


def test_cost_tracker_emits_cost_record():
    """CostTracker.record() emits cost_record to bus."""
    from pyagent_trace.cost import CostTracker

    bus = TraceEventBus()
    received: list[TraceEvent] = []
    bus.subscribe(received.append)

    tracker = CostTracker(event_bus=bus)
    tracker.record("debate", "bull", "gpt-4o", 500, 200, 0.003)

    assert len(received) == 1
    event = received[0]
    assert event.event_type == "cost_record"
    assert event.agent_name == "bull"
    assert event.pattern_type == "debate"
    assert event.payload["model"] == "gpt-4o"
    assert event.payload["input_tokens"] == 500
    assert event.payload["output_tokens"] == 200
    assert event.payload["cost_usd"] == 0.003


def test_cost_tracker_no_bus_still_works():
    """CostTracker without bus still records entries (backward compat)."""
    from pyagent_trace.cost import CostTracker

    tracker = CostTracker()  # no bus
    tracker.record("debate", "bull", "gpt-4o", 500, 200, 0.003)

    assert tracker.total_cost == pytest.approx(0.003)
    assert tracker.total_tokens == 700
