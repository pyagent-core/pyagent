"""Overview page — blueprint summary and quick actions."""

from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/")
async def overview(request: Request):
    """Render the overview dashboard page."""
    templates = request.app.state.templates
    # Default context when no blueprint is loaded
    ctx = {
        "request": request,
        "blueprint_name": "No blueprint loaded",
        "blueprint_version": "-",
        "owner": "-",
        "agent_count": 0,
        "workflow_count": 0,
        "provider_count": 0,
        "contract_count": 0,
        "valid": True,
        "issue_count": 0,
    }
    return templates.TemplateResponse("overview.html", ctx)
