"""Simulate page — run workflows with MockLLM or live LLMs."""

from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/")
async def simulate_page(request: Request):
    """Render simulation form."""
    templates = request.app.state.templates
    return templates.TemplateResponse("simulate.html", {"request": request})
