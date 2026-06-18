"""Agents page — list and detail views for blueprint agents."""

from __future__ import annotations

from fastapi import APIRouter, Request

from pyagent_studio.web.routes._common import base_context, get_blueprint_service

router = APIRouter()


@router.get("/")
async def agents_list(request: Request):
    """List all agents from the loaded blueprint."""
    templates = request.app.state.templates
    bp = get_blueprint_service(request)
    spec = bp.spec if bp else None
    ctx = base_context(request)
    ctx.update({"agents": spec.agents if spec else {}, "selected": None})
    return templates.TemplateResponse(request, "agents.html", context=ctx)


@router.get("/{name}")
async def agent_detail(request: Request, name: str):
    """Agent detail view."""
    templates = request.app.state.templates
    bp = get_blueprint_service(request)
    spec = bp.spec if bp else None
    ctx = base_context(request)
    ctx.update({"agents": spec.agents if spec else {}, "selected": name})
    return templates.TemplateResponse(request, "agents.html", context=ctx)
