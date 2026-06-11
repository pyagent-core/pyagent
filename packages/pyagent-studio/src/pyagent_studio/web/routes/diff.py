"""Diff page — semantic diff between two blueprints."""

from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/")
async def diff_page(request: Request):
    """Render diff page."""
    templates = request.app.state.templates
    return templates.TemplateResponse(request, "diff.html", context={})
