"""Tests for RunsService: trace aggregation into dashboard metrics."""

from __future__ import annotations

from pathlib import Path

import pytest
from pyagent_studio.services.runs_service import RunsService

_FIXTURE = (
    Path(__file__).resolve().parent.parent.parent.parent / "examples" / "fixtures" / "sample_trace.jsonl"
)


@pytest.fixture
def loaded_service():
    if not _FIXTURE.exists():
        pytest.skip("fixture not found")
    svc = RunsService()
    svc.load(_FIXTURE)
    return svc


# --- Sample-data fallback ---


def test_no_trace_loaded_uses_sample_data():
    """Without loading a trace, dashboard_context falls back to sample data."""
    svc = RunsService()
    ctx = svc.dashboard_context()
    assert ctx["using_sample_data"] is True
    assert ctx["kpis"]["total_runs"]["value"] == "1,248"


def test_loaded_trace_is_not_sample_data(loaded_service):
    ctx = loaded_service.dashboard_context()
    assert ctx["using_sample_data"] is False


# --- KPI math ---


def test_kpis_total_runs(loaded_service):
    ctx = loaded_service.dashboard_context()
    assert ctx["kpis"]["total_runs"]["value"] == "2"


def test_kpis_success_rate(loaded_service):
    ctx = loaded_service.dashboard_context()
    # 1 success out of 2 runs
    assert ctx["kpis"]["success_rate"]["value"] == "50.0%"


def test_kpis_total_cost(loaded_service):
    ctx = loaded_service.dashboard_context()
    # 0.0021 + 0.0185 + 0.0042
    assert ctx["kpis"]["total_cost"]["value"] == "$0.02"


def test_kpis_total_tokens(loaded_service):
    ctx = loaded_service.dashboard_context()
    # (200+120) + (600+380) + (300+240) = 1840
    assert ctx["kpis"]["total_tokens"]["value"] == "1,840"


# --- Recent runs ---


def test_recent_runs_includes_both_runs(loaded_service):
    ctx = loaded_service.dashboard_context()
    run_ids = {r["run_id"] for r in ctx["recent_runs"]}
    assert run_ids == {"run_fixture_1", "run_fixture_2"}


def test_recent_runs_status(loaded_service):
    ctx = loaded_service.dashboard_context()
    by_id = {r["run_id"]: r for r in ctx["recent_runs"]}
    assert by_id["run_fixture_1"]["status"] == "success"
    assert by_id["run_fixture_2"]["status"] == "failed"


# --- Cost breakdown / top agents ---


def test_cost_breakdown_by_provider(loaded_service):
    ctx = loaded_service.dashboard_context()
    providers = {row["provider"] for row in ctx["cost_breakdown"]}
    assert providers == {"OpenAI", "Anthropic", "Google"}


def test_top_agents_by_cost_ranked(loaded_service):
    ctx = loaded_service.dashboard_context()
    names = [row["agent_name"] for row in ctx["top_agents"]]
    assert names[0] == "Billing Agent"  # highest cost (0.0185)


# --- Provider health ---


def test_provider_health_flags_errors(loaded_service):
    ctx = loaded_service.dashboard_context()
    by_provider = {row["provider"]: row for row in ctx["provider_health"]}
    assert by_provider["Google"]["success_rate"] == 0.0
    assert by_provider["OpenAI"]["success_rate"] == 100.0


# --- Cost over time bucketing ---


def test_cost_over_time_is_cumulative_and_bounded(loaded_service):
    points = loaded_service._cost_over_time(buckets=12)
    assert 0 < len(points) <= 12
    values = [p["cost_usd"] for p in points]
    # Cumulative: monotonically non-decreasing
    assert values == sorted(values)
    # Final point equals total recorded cost
    total = sum(r["cost_usd"] for r in loaded_service._cost_records)
    assert values[-1] == pytest.approx(total, abs=1e-4)


# --- KPI deltas ---


def test_kpis_carry_delta_label(loaded_service):
    ctx = loaded_service.dashboard_context()
    assert ctx["kpis"]["total_runs"]["delta_label"] == "vs previous period"


# --- Run trace tree ---


def test_run_trace_defaults_to_latest_run(loaded_service):
    ctx = loaded_service.dashboard_context()
    assert ctx["run_trace"]["run_id"] == "run_fixture_2"
    pattern_node = ctx["run_trace"]["children"][0]
    assert pattern_node["name"] == "refund-processor"
    assert pattern_node["children"][0]["name"] == "Policy Checker"
    assert pattern_node["children"][0]["kind"] == "tool"
