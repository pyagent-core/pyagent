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


def test_app_has_routes(app):
    """All expected routes are registered."""
    route_paths = [r.path for r in app.routes]
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


def test_overview_shows_agent_count(client):
    """Overview page includes card grid."""
    response = client.get("/")
    assert "Agents" in response.text
    assert "Workflows" in response.text


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
    route_paths = [r.path for r in app.routes]
    assert "/traces/live" in route_paths


def test_traces_bus_accessible():
    """get_trace_bus() returns a TraceEventBus instance."""
    from pyagent_studio.web.routes.traces import get_trace_bus
    from pyagent_trace.events import TraceEventBus

    bus = get_trace_bus()
    assert isinstance(bus, TraceEventBus)
