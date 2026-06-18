"""Providers page — LLM provider bindings from the blueprint with model costs."""

from __future__ import annotations

from fastapi import APIRouter, Request

from pyagent_studio.web.routes._common import base_context, get_blueprint_service

router = APIRouter()


@router.get("/")
async def providers_page(request: Request):
    """Render providers page from the loaded blueprint."""
    templates = request.app.state.templates
    bp = get_blueprint_service(request)
    spec = bp.spec if bp else None

    try:
        from pyagent_studio.services.provider_service import ProviderService

        psvc: ProviderService | None = ProviderService()
    except Exception:
        psvc = None

    providers: list[dict] = []
    if spec is not None:
        for name, binding in spec.providers.items():
            cost = psvc.model_cost(binding.model) if psvc else {}
            in_cost = (cost.get("input_cost_per_token") or 0.0) * 1000
            out_cost = (cost.get("output_cost_per_token") or 0.0) * 1000
            providers.append(
                {
                    "name": name,
                    "provider": binding.provider or "—",
                    "model": binding.model,
                    "fallback": binding.fallback_ref or "—",
                    "input_cost_1k": f"${in_cost:.4f}" if in_cost else "—",
                    "output_cost_1k": f"${out_cost:.4f}" if out_cost else "—",
                }
            )

    ctx = base_context(request)
    ctx.update({"providers": providers})
    return templates.TemplateResponse(request, "providers.html", context=ctx)
