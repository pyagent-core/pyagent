"""Docs page — auto-rendered blueprint documentation."""

from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/")
async def docs_page(request: Request):
    """Render docs page."""
    templates = request.app.state.templates
    return templates.TemplateResponse(request, "docs.html", context={})
