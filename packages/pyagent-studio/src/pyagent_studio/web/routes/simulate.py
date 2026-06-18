"""Simulate page — run workflows with MockLLM or live LLMs."""

from __future__ import annotations

from fastapi import APIRouter, Request

from pyagent_studio.services.simulation_service import SimulationService
from pyagent_studio.web.routes._common import base_context, get_blueprint_service
from pyagent_studio.web.routes.traces import get_trace_bus

router = APIRouter()


@router.get("/")
async def simulate_page(request: Request):
    """Render simulation form."""
    templates = request.app.state.templates
    bp = get_blueprint_service(request)
    spec = bp.spec if bp else None
    ctx = base_context(request)
    ctx.update({"workflows": list(spec.workflows.keys()) if spec else []})
    return templates.TemplateResponse(request, "simulate.html", context=ctx)


@router.post("/run")
async def simulate_run(request: Request):
    """Run a workflow simulation and return the result partial."""
    templates = request.app.state.templates
    form = await request.form()
    workflow = str(form.get("workflow", "")).strip()
    task = str(form.get("task", "")).strip()
    use_live = form.get("mode") == "live"

    bp = get_blueprint_service(request)
    spec = bp.spec if bp else None

    if spec is None:
        result = {"success": False, "error": "No blueprint loaded."}
    elif not workflow or not task:
        result = {"success": False, "error": "Workflow and task are both required."}
    else:
        sim = SimulationService(event_bus=get_trace_bus(), use_live=use_live)
        res = await sim.run(spec, workflow, task)
        result = {
            "success": res.success,
            "output": res.output,
            "error": res.error,
            "elapsed_ms": round(res.elapsed_ms, 1),
            "workflow": res.workflow,
        }

    return templates.TemplateResponse(request, "_simulate_result.html", context={"result": result})
