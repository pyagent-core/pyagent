"""Overview page — live run metrics, cost charts, and quick actions."""

from __future__ import annotations

import csv
import io

from fastapi import APIRouter, Request
from starlette.responses import StreamingResponse

from pyagent_studio.services.runs_service import RunsService

router = APIRouter()

_runs_service = RunsService()

QUICK_ACTIONS = [
    {
        "icon": "🔍",
        "label": "Search Runs",
        "sub": "Find any run or trace",
        "href": "#runs-table",
        "enabled": True,
    },
    {
        "icon": "🔗",
        "label": "Drill into Trace",
        "sub": "Inspect every step",
        "href": "#run-trace-card",
        "enabled": True,
    },
    {
        "icon": "⚖️",
        "label": "Compare Runs",
        "sub": "Side-by-side analysis",
        "href": None,
        "enabled": False,
    },
    {
        "icon": "▶️",
        "label": "Replay with Mock",
        "sub": "Reproduce safely",
        "href": "/simulate/",
        "enabled": True,
    },
    {
        "icon": "✅",
        "label": "View Evaluations",
        "sub": "See quality results",
        "href": None,
        "enabled": False,
    },
    {
        "icon": "🔔",
        "label": "Create Alert",
        "sub": "Set up notifications",
        "href": None,
        "enabled": False,
    },
    {
        "icon": "⬇️",
        "label": "Export Data",
        "sub": "Download traces",
        "href": "/export/runs.csv",
        "enabled": True,
    },
    {
        "icon": "👥",
        "label": "Manage Access",
        "sub": "Roles & permissions",
        "href": None,
        "enabled": False,
    },
]


def _build_context(request: Request) -> dict:
    trace_path = getattr(request.app.state, "trace_path", None)
    if trace_path and not _runs_service.is_loaded:
        _runs_service.load(trace_path)

    ctx = _runs_service.dashboard_context()
    ctx["quick_actions"] = QUICK_ACTIONS
    return ctx


@router.get("/")
async def overview(request: Request):
    """Render the full Overview dashboard page."""
    templates = request.app.state.templates
    return templates.TemplateResponse(request, "overview.html", context=_build_context(request))


@router.get("/refresh")
async def overview_refresh(request: Request):
    """Return just the dashboard body partial, for HTMX polling."""
    templates = request.app.state.templates
    return templates.TemplateResponse(
        request, "_overview_body.html", context=_build_context(request)
    )


@router.get("/export/runs.csv")
async def export_runs_csv(request: Request):
    """Download recent runs as CSV."""
    ctx = _build_context(request)
    buffer = io.StringIO()
    writer = csv.DictWriter(
        buffer, fieldnames=["run_id", "workflow", "status", "duration_s", "cost_usd", "started_at"]
    )
    writer.writeheader()
    writer.writerows(ctx["recent_runs"])
    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=runs.csv"},
    )
