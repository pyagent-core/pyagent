"""Workflows page — list view with a Mermaid DAG of the blueprint."""

from __future__ import annotations

from fastapi import APIRouter, Request

from pyagent_studio.web.routes._common import base_context, get_blueprint_service

router = APIRouter()


def _mermaid_for(spec) -> str:
    if spec is None:
        return ""
    from pyagent_blueprint import BlueprintRenderer

    try:
        return BlueprintRenderer().to_mermaid(spec)
    except Exception:
        return ""


@router.get("/")
async def workflows_list(request: Request):
    """List all workflows."""
    templates = request.app.state.templates
    bp = get_blueprint_service(request)
    spec = bp.spec if bp else None
    ctx = base_context(request)
    ctx.update(
        {
            "workflows": spec.workflows if spec else {},
            "mermaid": _mermaid_for(spec),
            "selected": None,
        }
    )
    return templates.TemplateResponse(request, "workflows.html", context=ctx)


@router.get("/{name}")
async def workflow_detail(request: Request, name: str):
    """Workflow detail with Mermaid DAG."""
    templates = request.app.state.templates
    bp = get_blueprint_service(request)
    spec = bp.spec if bp else None
    ctx = base_context(request)
    ctx.update(
        {
            "workflows": spec.workflows if spec else {},
            "mermaid": _mermaid_for(spec),
            "selected": name,
        }
    )
    return templates.TemplateResponse(request, "workflows.html", context=ctx)
