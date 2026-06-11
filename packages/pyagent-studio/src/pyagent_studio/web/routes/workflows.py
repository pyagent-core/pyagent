"""Workflows page — list and detail views for blueprint workflows."""

from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/")
async def workflows_list(request: Request):
    """List all workflows."""
    templates = request.app.state.templates
    return templates.TemplateResponse(request, "workflows.html", context={"workflows": {}})


@router.get("/{name}")
async def workflow_detail(request: Request, name: str):
    """Workflow detail with Mermaid DAG."""
    templates = request.app.state.templates
    return templates.TemplateResponse(
        request, "workflows.html", context={"workflows": {}, "selected": name}
    )
