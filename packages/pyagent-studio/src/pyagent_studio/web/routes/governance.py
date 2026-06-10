"""Governance page — compliance score and validation issues."""

from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/")
async def governance_page(request: Request):
    """Render governance page."""
    templates = request.app.state.templates
    return templates.TemplateResponse(
        "governance.html", {"request": request, "score": 100, "issues": []}
    )
