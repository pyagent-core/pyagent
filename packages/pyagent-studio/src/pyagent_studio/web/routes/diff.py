"""Diff page — semantic diff between two uploaded blueprints."""

from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import APIRouter, Request

from pyagent_studio.services.blueprint_service import BlueprintService
from pyagent_studio.services.governance_service import GovernanceService
from pyagent_studio.web.routes._common import base_context

router = APIRouter()


@router.get("/")
async def diff_page(request: Request):
    """Render diff upload form."""
    templates = request.app.state.templates
    return templates.TemplateResponse(request, "diff.html", context=base_context(request))


async def _save_upload(upload, suffix: str) -> Path:
    data = await upload.read()
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(data)
    tmp.close()
    return Path(tmp.name)


@router.post("/compare")
async def diff_compare(request: Request):
    """Compare two uploaded blueprints and return the diff partial."""
    templates = request.app.state.templates
    form = await request.form()
    old_f = form.get("old")
    new_f = form.get("new")

    ctx: dict = {"summary": "", "changes": [], "error": None}
    if not old_f or not new_f or not getattr(old_f, "filename", "") or not getattr(new_f, "filename", ""):
        ctx["error"] = "Please choose two blueprint files to compare."
        return templates.TemplateResponse(request, "_diff_result.html", context=ctx)

    old_path = await _save_upload(old_f, Path(old_f.filename).suffix or ".yaml")
    new_path = await _save_upload(new_f, Path(new_f.filename).suffix or ".yaml")
    try:
        old_spec = BlueprintService().load(old_path)
        new_spec = BlueprintService().load(new_path)
        gov = GovernanceService()
        ctx["summary"] = gov.diff_summary(old_spec, new_spec)
        ctx["changes"] = [
            {
                "path": c.path,
                "change_type": str(c.change_type).split(".")[-1],
                "old_value": c.old_value,
                "new_value": c.new_value,
                "severity": str(c.severity).split(".")[-1],
            }
            for c in gov.diff(old_spec, new_spec)
        ]
    except Exception as exc:
        ctx["error"] = f"Could not compare blueprints: {exc}"
    finally:
        old_path.unlink(missing_ok=True)
        new_path.unlink(missing_ok=True)

    return templates.TemplateResponse(request, "_diff_result.html", context=ctx)
