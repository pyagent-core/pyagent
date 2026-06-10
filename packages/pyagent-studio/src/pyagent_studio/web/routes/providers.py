"""Providers page — LLM provider list and health checks."""

from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/")
async def providers_page(request: Request):
    """Render providers page."""
    templates = request.app.state.templates
    return templates.TemplateResponse("providers.html", {"request": request, "providers": []})
