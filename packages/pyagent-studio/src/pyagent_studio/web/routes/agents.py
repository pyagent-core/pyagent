"""Agents page — list and detail views for blueprint agents."""

from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/")
async def agents_list(request: Request):
    """List all agents."""
    templates = request.app.state.templates
    return templates.TemplateResponse(request, "agents.html", context={"agents": {}})


@router.get("/{name}")
async def agent_detail(request: Request, name: str):
    """Agent detail view."""
    templates = request.app.state.templates
    return templates.TemplateResponse(
        request, "agents.html", context={"agents": {}, "selected": name}
    )
