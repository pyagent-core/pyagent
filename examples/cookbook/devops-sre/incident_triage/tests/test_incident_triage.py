"""Tests for incident_triage — MockLLM only, no real LLM calls."""
from __future__ import annotations
import asyncio
import pytest

from pyagent_patterns.base import Agent, MockLLM
from pyagent_patterns.orchestration import Pipeline
from pyagent_patterns.advanced import HumanInTheLoop
from pyagent_patterns.advanced.human_in_the_loop import HumanDecision
from pyagent_trace import CostTracker
from pyagent_trace.events import TraceEventBus

from ..models import parse_touches_prod, parse_approved, TriageRequest, TriageResponse


# ── parse_touches_prod ────────────────────────────────────────────────────────

def test_non_prod_detected():
    assert parse_touches_prod("TOUCHES_PROD: no\nRestart staging replica.") is False


def test_prod_detected():
    assert parse_touches_prod("TOUCHES_PROD: yes\nRollback payments-svc.") is True


def test_missing_marker_defaults_to_non_prod():
    assert parse_touches_prod("Investigate DB connection pool.") is False


# ── Pipeline triage ──────────────────────────────────────────────────────────

def test_pipeline_three_stages():
    mock = MockLLM(responses=[
        "payments-svc: 5xx since 14 min, pool at 100/100.",
        "Root cause: connection pool exhausted after deploy.",
        "TOUCHES_PROD: no\nRestart payments-svc replica.",
    ])
    pipe = Pipeline(stages=[
        Agent("log_analyst", mock, system_prompt=""),
        Agent("root_cause",  mock, system_prompt=""),
        Agent("remediation", mock, system_prompt=""),
    ])
    result = asyncio.run(pipe.run("ALERT: checkout 5xx rate 12%."))
    assert "TOUCHES_PROD" in result.output or "pool" in result.output.lower()


def test_non_prod_skips_human_gate():
    called = []

    def gate(out, meta):
        called.append(out)
        return HumanDecision(approved=True, modified_output=out)

    mock = MockLLM(responses=["TOUCHES_PROD: no\nRestart replica in staging."])
    hitl = HumanInTheLoop(
        agent=Agent("runbook_writer", mock, system_prompt=""),
        review_fn=gate,
        high_risk_keywords=["delete", "drop"],
    )
    result = asyncio.run(hitl.run("Remediation: non-prod change."))
    assert result is not None


def test_cost_tracker_four_agents():
    bus     = TraceEventBus()
    tracker = CostTracker(event_bus=bus)

    for name, cost in [("log_analyst", 0.00010), ("root_cause", 0.00350),
                       ("remediation", 0.00290), ("runbook_writer", 0.00008)]:
        tracker.record("incident_triage", name, "mock-model", 200, 80, cost)

    assert tracker.total_cost == pytest.approx(0.00658, abs=1e-5)
    assert len(tracker.by_agent()) == 4


# ── Pydantic models ───────────────────────────────────────────────────────────

def test_triage_request_schema():
    req = TriageRequest(incident_id="INC-042", alert="5xx rate 12%.")
    assert req.incident_id == "INC-042"


def test_triage_response_schema():
    resp = TriageResponse(
        incident_id="INC-042",
        runbook="Rollback payments-svc.",
        touches_prod=True,
        approved=True,
        cost_usd=0.00658,
        trace_file="traces/incidents/INC-042/abc.jsonl",
    )
    assert resp.touches_prod is True
    assert resp.approved is True
