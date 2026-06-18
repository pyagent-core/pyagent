"""Tests for the PyAgent Studio web dashboard."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from pyagent_studio.web.app import create_app
from starlette.testclient import TestClient


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
def client(app):
    return TestClient(app)


# --- App factory ---


def test_app_factory_creates_app(app):
    """create_app() returns FastAPI instance."""
    assert isinstance(app, FastAPI)
    assert app.title == "PyAgent Studio"


def _all_route_paths(app):
    """Registered route paths via the OpenAPI schema (version-robust)."""
    return list(app.openapi()["paths"].keys())


def test_app_has_routes(app):
    """All expected routes are registered."""
    route_paths = _all_route_paths(app)
    for path in [
        "/",
        "/agents",
        "/workflows",
        "/simulate",
        "/traces",
        "/governance",
        "/providers",
        "/diff",
        "/docs",
    ]:
        # Routers with prefix register as /prefix/ or /prefix
        matching = [r for r in route_paths if r.rstrip("/") == path.rstrip("/") or r == path]
        assert matching, f"Missing route: {path}"


# --- Overview ---


def test_overview_page_renders(client):
    """GET / returns 200."""
    response = client.get("/")
    assert response.status_code == 200
    assert "PyAgent Studio" in response.text


def test_overview_shows_kpis(client):
    """Overview page includes the KPI row."""
    response = client.get("/")
    assert "Total Runs" in response.text
    assert "Success Rate" in response.text


def test_overview_shows_sample_data_banner_by_default(client):
    """With no trace loaded, the sample-data banner is shown."""
    response = client.get("/")
    assert "Showing sample data" in response.text


def test_overview_refresh_partial(client):
    """GET /refresh returns just the dashboard body fragment."""
    response = client.get("/refresh")
    assert response.status_code == 200
    assert "Total Runs" in response.text
    assert "<nav" not in response.text


def test_export_runs_csv(client):
    """GET /export/runs.csv returns a CSV attachment."""
    response = client.get("/export/runs.csv")
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert "run_id" in response.text


# --- Blueprint-backed resource tabs (bundled sample loaded by default) ---


def test_sample_blueprint_banner(client):
    """Resource pages show the sample-blueprint banner when no --blueprint given."""
    response = client.get("/agents/")
    assert "sample blueprint" in response.text


def test_agents_page_shows_real_agents(client):
    """Agents page lists agents from the bundled sample blueprint."""
    response = client.get("/agents/")
    assert "classifier" in response.text
    assert "billing" in response.text


def test_agent_detail_shows_prompt(client):
    """Agent detail view shows the selected agent's prompt."""
    response = client.get("/agents/billing")
    assert response.status_code == 200
    assert "billing inquiries" in response.text.lower() or "Billing" in response.text


def test_workflows_page_shows_real_workflows(client):
    """Workflows page lists workflows from the sample blueprint."""
    response = client.get("/workflows/")
    assert "customer-support" in response.text
    assert "supervisor" in response.text


def test_providers_page_shows_models(client):
    """Providers page lists the blueprint's models."""
    response = client.get("/providers/")
    assert "claude-3-5-sonnet" in response.text
    assert "gpt-4o-mini" in response.text


def test_governance_uses_real_service(client):
    """Governance page computes a real compliance score for the sample."""
    response = client.get("/governance/")
    assert "Compliance Score" in response.text
    assert "100%" in response.text


def test_docs_page_renders_markdown(client):
    """Docs page renders auto-generated markdown from the blueprint."""
    response = client.get("/docs/")
    assert "customer-support" in response.text


def test_simulate_run_returns_result(client):
    """POST /simulate/run executes a MockLLM run and returns a result partial."""
    response = client.post(
        "/simulate/run",
        data={"workflow": "customer-support", "task": "help", "mode": "mock"},
    )
    assert response.status_code == 200
    assert "Success" in response.text
    assert "Mock response" in response.text


def test_simulate_run_requires_fields(client):
    """POST /simulate/run with missing task returns a failure result."""
    response = client.post("/simulate/run", data={"workflow": "", "task": "", "mode": "mock"})
    assert response.status_code == 200
    assert "Failed" in response.text


def test_diff_compare_identical(client):
    """POST /diff/compare with identical blueprints reports no changes."""
    from pathlib import Path

    bp = (
        Path(__file__).resolve().parent.parent
        / "src"
        / "pyagent_studio"
        / "data"
        / "sample_blueprint.yaml"
    )
    content = bp.read_bytes()
    response = client.post(
        "/diff/compare",
        files={
            "old": ("a.yaml", content, "application/x-yaml"),
            "new": ("b.yaml", content, "application/x-yaml"),
        },
    )
    assert response.status_code == 200
    assert "No changes" in response.text


def test_traces_page_loads_sse_extension(client):
    """Traces page loads the htmx SSE extension."""
    response = client.get("/traces/")
    assert "htmx-ext-sse" in response.text


# --- Agents ---


def test_agents_page_renders(client):
    """GET /agents returns 200."""
    response = client.get("/agents/")
    assert response.status_code == 200
    assert "Agents" in response.text


def test_agent_detail_page(client):
    """GET /agents/{name} returns 200."""
    response = client.get("/agents/test_agent")
    assert response.status_code == 200


# --- Workflows ---


def test_workflows_page_renders(client):
    """GET /workflows returns 200."""
    response = client.get("/workflows/")
    assert response.status_code == 200
    assert "Workflows" in response.text


def test_workflow_detail_page(client):
    """GET /workflows/{name} returns 200."""
    response = client.get("/workflows/test_wf")
    assert response.status_code == 200


# --- Simulate ---


def test_simulate_page_renders(client):
    """GET /simulate returns 200 with form."""
    response = client.get("/simulate/")
    assert response.status_code == 200
    assert "Simulate" in response.text
    assert "MockLLM" in response.text


# --- Traces ---


def test_traces_page_renders(client):
    """GET /traces returns 200."""
    response = client.get("/traces/")
    assert response.status_code == 200
    assert "Traces" in response.text


# --- Governance ---


def test_governance_page_renders(client):
    """GET /governance returns 200."""
    response = client.get("/governance/")
    assert response.status_code == 200
    assert "Governance" in response.text


def test_governance_shows_score(client):
    """Governance page displays compliance score."""
    response = client.get("/governance/")
    assert "100%" in response.text


# --- Providers ---


def test_providers_page_renders(client):
    """GET /providers returns 200."""
    response = client.get("/providers/")
    assert response.status_code == 200
    assert "Providers" in response.text


# --- Diff ---


def test_diff_page_renders(client):
    """GET /diff returns 200."""
    response = client.get("/diff/")
    assert response.status_code == 200
    assert "Diff" in response.text


# --- Docs ---


def test_docs_page_renders(client):
    """GET /docs returns 200."""
    response = client.get("/docs/")
    assert response.status_code == 200
    assert "Documentation" in response.text


def test_docs_contains_mermaid(client):
    """Docs page includes mermaid.js."""
    response = client.get("/docs/")
    assert "mermaid" in response.text


# --- Static files ---


def test_static_css_served(client):
    """GET /static/style.css returns 200."""
    response = client.get("/static/style.css")
    assert response.status_code == 200
    assert "dashboard-layout" in response.text


def test_static_htmx_served(client):
    """GET /static/htmx.min.js returns 200."""
    response = client.get("/static/htmx.min.js")
    assert response.status_code == 200


# --- Sidebar navigation ---


def test_base_template_sidebar(client):
    """All pages contain sidebar navigation links."""
    response = client.get("/")
    for link in [
        "/agents",
        "/workflows",
        "/simulate",
        "/traces",
        "/governance",
        "/providers",
        "/diff",
        "/docs",
    ]:
        assert link in response.text, f"Sidebar missing link: {link}"


# --- Traces SSE ---


def test_traces_live_sse_endpoint_registered(app):
    """SSE endpoint /traces/live is registered as a route."""
    assert "/traces/live" in _all_route_paths(app)


def test_traces_bus_accessible():
    """get_trace_bus() returns a TraceEventBus instance."""
    from pyagent_studio.web.routes.traces import get_trace_bus
    from pyagent_trace.events import TraceEventBus

    bus = get_trace_bus()
    assert isinstance(bus, TraceEventBus)
