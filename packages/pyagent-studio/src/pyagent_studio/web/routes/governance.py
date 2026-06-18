"""Governance page — compliance score and validation issues."""

from __future__ import annotations

from fastapi import APIRouter, Request

from pyagent_studio.services.governance_service import GovernanceService
from pyagent_studio.web.routes._common import base_context, get_blueprint_service

router = APIRouter()


@router.get("/")
async def governance_page(request: Request):
    """Render governance page with real compliance results."""
    templates = request.app.state.templates
    bp = get_blueprint_service(request)
    spec = bp.spec if bp else None

    score = 0
    passed = 0
    total = 0
    issues: list[dict] = []
    if spec is not None:
        report = GovernanceService().check_compliance(spec)
        score = round(report.score * 100)
        passed = report.passed
        total = report.total_checks
        issues = [
            {"severity": str(i.severity).split(".")[-1], "path": i.path, "message": i.message}
            for i in report.issues
        ]

    ctx = base_context(request)
    ctx.update({"score": score, "passed": passed, "total": total, "issues": issues})
    return templates.TemplateResponse(request, "governance.html", context=ctx)
