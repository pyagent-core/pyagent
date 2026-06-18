"""Docs page — auto-rendered blueprint documentation."""

from __future__ import annotations

from fastapi import APIRouter, Request

from pyagent_studio.web.routes._common import base_context, get_blueprint_service

router = APIRouter()


@router.get("/")
async def docs_page(request: Request):
    """Render auto-generated documentation from the loaded blueprint."""
    templates = request.app.state.templates
    bp = get_blueprint_service(request)
    spec = bp.spec if bp else None

    markdown = ""
    mermaid = ""
    if spec is not None:
        from pyagent_blueprint import BlueprintRenderer

        renderer = BlueprintRenderer()
        try:
            markdown = renderer.to_markdown(spec)
        except Exception:
            markdown = ""
        try:
            mermaid = renderer.to_mermaid(spec)
        except Exception:
            mermaid = ""

    ctx = base_context(request)
    ctx.update({"markdown": markdown, "mermaid": mermaid})
    return templates.TemplateResponse(request, "docs.html", context=ctx)
