"""Tests for log_triage — MockLLM only, no real LLM calls."""
from __future__ import annotations
import asyncio
import pytest

from pyagent_patterns.base import Agent, MockLLM
from pyagent_patterns.orchestration import Pipeline
from pyagent_trace import CostTracker
from pyagent_trace.events import TraceEventBus

from ..models import AlertRequest, AlertResponse, parse_disposition


def test_parse_disposition_false_positive():
    assert parse_disposition("FALSE_POSITIVE: VPN IP rotation.") == "FALSE_POSITIVE"


def test_parse_disposition_escalate():
    assert parse_disposition("ESCALATE: impossible travel + MFA failure.") == "ESCALATE"


def test_parse_disposition_default_escalate():
    assert parse_disposition("Suspicious activity detected.") == "ESCALATE"


def test_pipeline_three_stages_escalate():
    mock = MockLLM(responses=[
        "Asset: vpn-gw-01. Severity: 5.",
        "Confidence 92: matches T1110.003.",
        "ESCALATE: likely account takeover.",
    ])
    pipe = Pipeline(stages=[
        Agent("enricher",   mock, system_prompt=""),
        Agent("correlator", mock, system_prompt=""),
        Agent("classifier", mock, system_prompt=""),
    ])
    result = asyncio.run(pipe.run('{"rule":"impossible_travel"}'))
    assert parse_disposition(result.output) == "ESCALATE"


def test_pipeline_false_positive_auto_closed():
    mock = MockLLM(responses=[
        "Asset: dev-box. Severity: 1.",
        "Confidence 25: no attack patterns.",
        "FALSE_POSITIVE: VPN provider IP rotation.",
    ])
    pipe = Pipeline(stages=[
        Agent("enricher",   mock, system_prompt=""),
        Agent("correlator", mock, system_prompt=""),
        Agent("classifier", mock, system_prompt=""),
    ])
    result = asyncio.run(pipe.run('{"rule":"geo_anomaly"}'))
    assert parse_disposition(result.output) == "FALSE_POSITIVE"


def test_cost_tracker_four_agents():
    bus     = TraceEventBus()
    tracker = CostTracker(event_bus=bus)
    tracker.record("log_triage", "enricher",    "gpt-4o-mini",              100,  40, 0.00009)
    tracker.record("log_triage", "correlator",  "claude-sonnet-4-20250514", 300, 120, 0.00255)
    tracker.record("log_triage", "classifier",  "claude-sonnet-4-20250514", 280, 110, 0.00238)
    tracker.record("log_triage", "case_writer", "gpt-4o-mini",               80,  30, 0.00007)
    assert tracker.total_cost == pytest.approx(0.00509, abs=1e-5)
    assert len(tracker.by_agent()) == 4


def test_alert_request_schema():
    req = AlertRequest(alert_id="ALERT-001", raw_alert='{"rule":"impossible_travel"}')
    assert req.alert_id == "ALERT-001"
