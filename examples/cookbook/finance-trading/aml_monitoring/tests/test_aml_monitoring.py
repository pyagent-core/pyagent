"""AML Monitoring tests — deterministic, no real LLM calls."""
from __future__ import annotations
import asyncio
import pytest

from pyagent_patterns.advanced import HumanInTheLoop
from pyagent_patterns.advanced.human_in_the_loop import HumanDecision
from pyagent_patterns.base import Agent, MockLLM
from pyagent_patterns.orchestration import Pipeline
from pyagent_trace import CostTracker
from pyagent_trace.events import TraceEventBus

from ..models import parse_tier


# ── parse_tier unit tests ────────────────────────────────────────────────────

def test_parse_tier_high():
    assert parse_tier("Risk: 88 — High. Drivers: structuring.") == "High"

def test_parse_tier_low():
    assert parse_tier("Risk: 15 — Low. Drivers: known payee.") == "Low"

def test_parse_tier_medium_fallback():
    assert parse_tier("No explicit tier mentioned.") == "Medium"

def test_parse_tier_numeric():
    assert parse_tier("score: 80 — suspicious transfer") == "High"


# ── Pipeline tests ────────────────────────────────────────────────────────────

def test_low_risk_auto_cleared(low_risk_mock):
    pipeline = Pipeline(stages=[
        Agent("rule_screener", low_risk_mock, system_prompt=""),
        Agent("risk_scorer",   low_risk_mock, system_prompt=""),
        Agent("enrichment",    low_risk_mock, system_prompt=""),
    ])
    result = asyncio.run(pipeline.run("$500 to ACME Corp"))
    assert "Low" in result.output
    assert parse_tier(result.output) == "Low"


def test_high_risk_reaches_sar_drafter(high_risk_mock):
    hitl_triggered = []

    def review_fn(out: str, meta: dict) -> HumanDecision:
        hitl_triggered.append(True)
        return HumanDecision(approved=True, modified_output=out)

    pipeline = Pipeline(stages=[
        Agent("rule_screener", high_risk_mock, system_prompt=""),
        Agent("risk_scorer",   high_risk_mock, system_prompt=""),
        Agent("enrichment",    high_risk_mock, system_prompt=""),
    ])
    sar_writer = HumanInTheLoop(
        agent=Agent("sar_drafter", high_risk_mock, system_prompt=""),
        review_fn=review_fn,
        high_risk_keywords=["High"],
    )

    result = asyncio.run(pipeline.run("$9,850 to Cyprus entity"))
    assert parse_tier(result.output) == "High"

    asyncio.run(sar_writer.run(result.output))
    assert hitl_triggered, "High-risk alert must trigger human review"


def test_high_risk_rejected_does_not_file_sar(high_risk_mock):
    def reject_fn(out: str, meta: dict) -> HumanDecision:
        return HumanDecision(approved=False, modified_output=out)

    sar_writer = HumanInTheLoop(
        agent=Agent("sar_drafter", high_risk_mock, system_prompt=""),
        review_fn=reject_fn,
        high_risk_keywords=["High"],
    )
    pipeline = Pipeline(stages=[
        Agent("rule_screener", high_risk_mock, system_prompt=""),
        Agent("risk_scorer",   high_risk_mock, system_prompt=""),
        Agent("enrichment",    high_risk_mock, system_prompt=""),
    ])
    triage = asyncio.run(pipeline.run("$9,850 to Cyprus entity"))
    sar_result = asyncio.run(sar_writer.run(triage.output))
    assert not sar_result.metadata.get("approved", True)


# ── Cost tracker test ─────────────────────────────────────────────────────────

def test_cost_tracker_records_all_agents():
    bus     = TraceEventBus()
    tracker = CostTracker(event_bus=bus)
    tracker.record("pipeline", "rule_screener", "gpt-4o-mini",    300, 100, 0.00023)
    tracker.record("pipeline", "risk_scorer",   "claude-sonnet",  500, 200, 0.00390)
    tracker.record("pipeline", "enrichment",    "gpt-4o-mini",    300,  80, 0.00019)

    assert tracker.total_cost == pytest.approx(0.00432, abs=1e-5)
    assert set(tracker.by_agent().keys()) == {"rule_screener", "risk_scorer", "enrichment"}
    assert tracker.total_tokens == 1380
