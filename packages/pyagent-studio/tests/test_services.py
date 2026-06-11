"""Tests for studio services: blueprint, simulation, trace, governance."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest
from pyagent_studio.services.blueprint_service import BlueprintService
from pyagent_studio.services.governance_service import GovernanceService
from pyagent_studio.services.simulation_service import SimulationService
from pyagent_studio.services.trace_service import TraceService

FIXTURES = Path(__file__).parent.parent.parent / "pyagent-blueprint" / "tests" / "fixtures"


# ── BlueprintService ─────────────────────────────────────────────────


def test_blueprint_service_load() -> None:
    svc = BlueprintService()
    spec = svc.load(FIXTURES / "customer_support.yaml")
    assert spec.metadata.name == "customer-support"
    assert svc.spec is not None


def test_blueprint_service_validate() -> None:
    svc = BlueprintService()
    svc.load(FIXTURES / "customer_support.yaml")
    issues = svc.validate()
    # customer_support.yaml is valid
    assert isinstance(issues, list)


def test_blueprint_service_compile() -> None:
    svc = BlueprintService()
    svc.load(FIXTURES / "customer_support.yaml")
    graph = svc.compile()
    assert "support" in graph


def test_blueprint_service_summary() -> None:
    svc = BlueprintService()
    assert svc.summary()["loaded"] is False
    svc.load(FIXTURES / "customer_support.yaml")
    summary = svc.summary()
    assert summary["loaded"] is True
    assert summary["agents"] == 3


def test_blueprint_service_discover() -> None:
    svc = BlueprintService()
    files = svc.discover_blueprints(FIXTURES)
    assert len(files) >= 2  # customer_support.yaml, research_agent.yaml


# ── SimulationService ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_simulation_service_run() -> None:
    svc = BlueprintService()
    spec = svc.load(FIXTURES / "research_agent.yaml")

    sim = SimulationService()
    result = await sim.run(spec, "research", "Explain quantum computing")
    assert result.success
    assert result.output
    assert result.elapsed_ms >= 0


@pytest.mark.asyncio
async def test_simulation_service_run_all() -> None:
    svc = BlueprintService()
    spec = svc.load(FIXTURES / "research_agent.yaml")

    sim = SimulationService()
    results = await sim.run_all(spec, {"research": "Test task"})
    assert len(results) == 1
    assert results[0].success


# ── TraceService ─────────────────────────────────────────────────────


def test_trace_service_load() -> None:
    with tempfile.NamedTemporaryFile(suffix=".jsonl", mode="w", delete=False) as f:
        f.write(
            json.dumps(
                {
                    "event_type": "llm_call",
                    "agent_name": "agent_1",
                    "tokens": 100,
                    "duration_ms": 50.0,
                    "timestamp": "2025-01-01T00:00:00",
                }
            )
            + "\n"
        )
        f.write(
            json.dumps(
                {
                    "event_type": "pattern_start",
                    "agent_name": "supervisor",
                    "tokens": 0,
                    "timestamp": "2025-01-01T00:00:01",
                }
            )
            + "\n"
        )
        f.flush()

        svc = TraceService()
        spans = svc.load(f.name)
        assert len(spans) == 2
        assert spans[0].event_type == "llm_call"
        assert spans[0].tokens == 100


def test_trace_service_query() -> None:
    with tempfile.NamedTemporaryFile(suffix=".jsonl", mode="w", delete=False) as f:
        f.write(json.dumps({"event_type": "llm_call", "agent_name": "a1", "tokens": 50}) + "\n")
        f.write(json.dumps({"event_type": "pattern_start", "agent_name": "a2"}) + "\n")
        f.flush()

        svc = TraceService()
        svc.load(f.name)
        results = svc.query(event_type="llm_call")
        assert len(results) == 1
        results = svc.query(agent_name="a2")
        assert len(results) == 1


def test_trace_service_summary() -> None:
    with tempfile.NamedTemporaryFile(suffix=".jsonl", mode="w", delete=False) as f:
        f.write(
            json.dumps(
                {"event_type": "llm_call", "agent_name": "a1", "tokens": 100, "duration_ms": 50}
            )
            + "\n"
        )
        f.flush()

        svc = TraceService()
        svc.load(f.name)
        summary = svc.summary()
        assert summary["count"] == 1
        assert summary["total_tokens"] == 100


def test_trace_service_missing_file() -> None:
    svc = TraceService()
    with pytest.raises(FileNotFoundError):
        svc.load("/nonexistent/file.jsonl")


# ── GovernanceService ────────────────────────────────────────────────


def test_governance_compliance() -> None:
    svc = BlueprintService()
    spec = svc.load(FIXTURES / "customer_support.yaml")

    gov = GovernanceService()
    report = gov.check_compliance(spec)
    assert 0.0 <= report.score <= 1.0
    assert report.total_checks > 0


def test_governance_diff() -> None:
    svc = BlueprintService()
    old_spec = svc.load(FIXTURES / "customer_support.yaml")
    new_spec = svc.load(FIXTURES / "research_agent.yaml")

    gov = GovernanceService()
    changes = gov.diff(old_spec, new_spec)
    assert len(changes) > 0


def test_governance_format_report() -> None:
    svc = BlueprintService()
    spec = svc.load(FIXTURES / "customer_support.yaml")

    gov = GovernanceService()
    report = gov.check_compliance(spec)
    text = gov.format_report(report)
    assert "Compliance Score" in text
