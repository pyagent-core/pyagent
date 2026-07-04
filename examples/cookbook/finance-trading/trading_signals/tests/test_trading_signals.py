"""Trading Signal Desk tests — deterministic, no real LLM calls."""
from __future__ import annotations
import asyncio
import pytest

from pyagent_patterns.base import Agent, MockLLM
from pyagent_patterns.orchestration import FanOutFanIn
from pyagent_trace import CostTracker
from pyagent_trace.events import TraceEventBus

from ..models import parse_conviction, parse_direction


def test_parse_direction_long():
    assert parse_direction("Consensus: LONG, conviction: 7/10") == "LONG"

def test_parse_direction_short():
    assert parse_direction("Direction: SHORT") == "SHORT"

def test_parse_direction_flat_default():
    assert parse_direction("No clear signal.") == "FLAT"

def test_parse_conviction():
    assert parse_conviction("Conviction: 8/10") == 8

def test_parse_conviction_default():
    assert parse_conviction("No conviction stated.") == 5


def test_bullish_consensus(bullish_mock):
    desk = FanOutFanIn(
        agents=[
            Agent("momentum",       bullish_mock, system_prompt=""),
            Agent("mean_reversion", bullish_mock, system_prompt=""),
            Agent("sentiment",      bullish_mock, system_prompt=""),
        ],
        aggregator=Agent("signal_aggregator", bullish_mock, system_prompt=""),
    )
    result = asyncio.run(desk.run("market data: bullish"))
    assert parse_direction(result.output) == "LONG"
    assert parse_conviction(result.output) >= 6


def test_bearish_consensus(bearish_mock):
    desk = FanOutFanIn(
        agents=[
            Agent("momentum",       bearish_mock, system_prompt=""),
            Agent("mean_reversion", bearish_mock, system_prompt=""),
            Agent("sentiment",      bearish_mock, system_prompt=""),
        ],
        aggregator=Agent("signal_aggregator", bearish_mock, system_prompt=""),
    )
    result = asyncio.run(desk.run("market data: bearish"))
    assert parse_direction(result.output) == "SHORT"


def test_cost_tracker_three_workers():
    bus     = TraceEventBus()
    tracker = CostTracker(event_bus=bus)
    tracker.record("fan_out", "momentum",        "gpt-4o-mini",   250, 80,  0.00015)
    tracker.record("fan_out", "mean_reversion",  "gpt-4o-mini",   250, 80,  0.00015)
    tracker.record("fan_out", "sentiment",       "gemini-flash",  300, 100, 0.00012)
    tracker.record("fan_in",  "signal_aggregator","claude-sonnet", 600, 200, 0.00510)

    assert tracker.total_cost == pytest.approx(0.00552, abs=1e-5)
    assert len(tracker.by_agent()) == 4
