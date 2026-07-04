"""Tests for clinical_summary — MockLLM only, no real LLM calls."""
from __future__ import annotations
import asyncio
import pytest

from pyagent_patterns.base import Agent, MockLLM
from pyagent_patterns.orchestration import Pipeline
from pyagent_patterns.resolution import SelfReflection
from pyagent_trace import CostTracker
from pyagent_trace.events import TraceEventBus

from ..models import SummaryRequest, SummaryResponse, parse_accurate, parse_safety_flags


def test_parse_accurate_true():
    assert parse_accurate("ACCURATE\nPatient: 68M, CHF. Meds: furosemide 40 mg.") is True


def test_parse_accurate_false():
    assert parse_accurate("Dose is incorrect. Correction: furosemide 80 mg.") is False


def test_parse_safety_flags_extracts():
    output = "ACCURATE\nSAFETY FLAGS:\n- Allergy not mentioned\n- Abnormal SpO2 flagged\n"
    flags = parse_safety_flags(output)
    assert len(flags) == 2
    assert any("Allergy" in f for f in flags)


def test_pipeline_two_stages():
    mock = MockLLM(responses=[
        "Diagnoses: CHF. Meds: furosemide 40 mg BID. Allergy: penicillin.",
        "68M CHF. Meds: furosemide 40 mg BID. Allergy: penicillin (rash). Follow-up: daily weights.",
    ])
    pipe = Pipeline(stages=[
        Agent("extractor", mock, system_prompt=""),
        Agent("drafter",   mock, system_prompt=""),
    ])
    result = asyncio.run(pipe.run("68M CHF..."))
    assert "furosemide" in result.output.lower() or "chf" in result.output.lower()


def test_self_reflection_one_round():
    mock = MockLLM(responses=[
        "ACCURATE\nSummary is correct.",
    ])
    reflect = SelfReflection(
        agent=Agent("summary_reviewer", mock, system_prompt=""),
        max_rounds=2,
        stop_phrase="ACCURATE",
    )
    result = asyncio.run(reflect.run("Draft: 68M CHF. Meds: furosemide 40 mg."))
    assert parse_accurate(result.output)


def test_self_reflection_two_rounds():
    mock = MockLLM(responses=[
        "Dose incorrect — should be furosemide 80 mg.",
        "ACCURATE\nAll values match source.",
    ])
    reflect = SelfReflection(
        agent=Agent("summary_reviewer", mock, system_prompt=""),
        max_rounds=2,
        stop_phrase="ACCURATE",
    )
    result = asyncio.run(reflect.run("Draft: 68M CHF."))
    assert parse_accurate(result.output)


def test_cost_tracker_three_agents():
    bus     = TraceEventBus()
    tracker = CostTracker(event_bus=bus)
    tracker.record("clinical_summary", "extractor",        "gpt-4o-mini",              200, 80,  0.00016)
    tracker.record("clinical_summary", "drafter",          "claude-sonnet-4-20250514", 350, 120, 0.00295)
    tracker.record("clinical_summary", "summary_reviewer", "claude-sonnet-4-20250514", 400, 150, 0.00340)
    assert tracker.total_cost == pytest.approx(0.00651, abs=1e-5)
    assert len(tracker.by_agent()) == 3


def test_summary_request_schema():
    req = SummaryRequest(patient_id="PAT-001", note="68M CHF...")
    assert req.patient_id == "PAT-001"
