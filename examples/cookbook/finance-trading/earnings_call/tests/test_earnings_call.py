"""Earnings Call Analyzer tests — deterministic, no real LLM calls."""
from __future__ import annotations
import asyncio
import pytest

from pyagent_patterns.base import Agent
from pyagent_patterns.resolution import SelfReflection
from pyagent_trace import CostTracker
from pyagent_trace.events import TraceEventBus

from ..models import STOP_PHRASE, is_complete


def test_is_complete_true():
    assert is_complete(f"Good analysis. {STOP_PHRASE}")

def test_is_complete_false():
    assert not is_complete("Partial analysis — missing risk section.")


def test_one_round_completes(one_round_mock):
    analyzer = SelfReflection(
        agent=Agent("earnings_analyst", one_round_mock, system_prompt=""),
        max_rounds=3,
        stop_phrase=STOP_PHRASE,
    )
    result = asyncio.run(analyzer.run("earnings transcript"))
    assert is_complete(result.output)
    assert result.metadata.get("rounds", 0) == 1


def test_two_rounds_until_complete(two_round_mock):
    analyzer = SelfReflection(
        agent=Agent("earnings_analyst", two_round_mock, system_prompt=""),
        max_rounds=3,
        stop_phrase=STOP_PHRASE,
    )
    result = asyncio.run(analyzer.run("earnings transcript"))
    assert is_complete(result.output)
    assert result.metadata.get("rounds", 0) == 2


def test_max_rounds_respected():
    from pyagent_patterns.base import MockLLM
    never_done = MockLLM(responses=["Draft 1.", "Draft 2.", "Draft 3."])
    analyzer = SelfReflection(
        agent=Agent("earnings_analyst", never_done, system_prompt=""),
        max_rounds=3,
        stop_phrase=STOP_PHRASE,
    )
    result = asyncio.run(analyzer.run("transcript"))
    assert result.metadata.get("rounds", 0) <= 3


def test_cost_tracker():
    bus     = TraceEventBus()
    tracker = CostTracker(event_bus=bus)
    tracker.record("self_reflection", "earnings_analyst", "claude-sonnet", 500, 200, 0.00390)
    tracker.record("self_reflection", "earnings_analyst", "claude-sonnet", 600, 250, 0.00480)
    assert tracker.total_cost == pytest.approx(0.00870, abs=1e-5)
