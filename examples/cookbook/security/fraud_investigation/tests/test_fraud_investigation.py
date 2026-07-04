"""Tests for fraud_investigation — MockLLM only, no real LLM calls."""
from __future__ import annotations
import pytest

from pyagent_trace import CostTracker
from pyagent_trace.events import TraceEventBus

from ..agents import anomaly_score, sanctions_check, transaction_lookup
from ..models import InvestigationRequest, InvestigationResponse, parse_risk_level


def test_parse_risk_level_high():
    assert parse_risk_level("Risk HIGH. Three structuring wires.") == "High"


def test_parse_risk_level_low():
    assert parse_risk_level("Risk LOW. Known vendor payment.") == "Low"


def test_parse_risk_level_default():
    assert parse_risk_level("Case file generated.") == "Medium"


def test_transaction_lookup_known():
    result = transaction_lookup("ACC-8842")
    assert "9,900" in result or "velocity" in result.lower()


def test_transaction_lookup_unknown():
    result = transaction_lookup("ACC-UNKNOWN")
    assert "No transactions" in result


def test_anomaly_score_high():
    result = anomaly_score("$9,900 transfer to new payee, new country login")
    assert "anomaly_score=" in result
    score = int(result.split("=")[1].split(" ")[0])
    assert score >= 60


def test_anomaly_score_low():
    result = anomaly_score("routine vendor payment")
    assert "anomaly_score=" in result
    score = int(result.split("=")[1].split(" ")[0])
    assert score <= 40


def test_sanctions_check_match():
    assert "MATCH" in sanctions_check("Shell Co Ltd")


def test_sanctions_check_clean():
    assert "no sanctions" in sanctions_check("Acme Corp").lower()


def test_cost_tracker_single_agent():
    bus     = TraceEventBus()
    tracker = CostTracker(event_bus=bus)
    tracker.record("fraud_investigation", "fraud_analyst", "gpt-4o", 800, 400, 0.01200)
    assert tracker.total_cost == pytest.approx(0.01200, abs=1e-6)


def test_investigation_request_schema():
    req = InvestigationRequest(alert_id="ALERT-001", alert="velocity rule triggered for ACC-8842")
    assert req.alert_id == "ALERT-001"
