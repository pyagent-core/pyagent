"""FastAPI router demonstrating direct authorization checks and tool routing."""

from __future__ import annotations

import time
from pathlib import Path

from fastapi import APIRouter
from pyagent_dns.authority import Action, CallContext, ResourceSelector
from pyagent_dns.blueprint import load_blueprint_dns
from pyagent_dns.middleware import DnsMiddleware

from .agents import build_tools
from .models import AuthorizationRequest, AuthorizationResponse

router = APIRouter(prefix="/security/tools", tags=["Tool Authorization"])

RECIPE_DIR = Path(__file__).resolve().parent
_bundle = load_blueprint_dns(RECIPE_DIR / "blueprint.yaml")
if _bundle is None:
    raise RuntimeError("Failed to load DNS bundle from blueprint.yaml")
_middleware = DnsMiddleware(_bundle.resolver, _bundle.graph)
_tools = build_tools()


@router.post("/authorize", response_model=AuthorizationResponse)
async def authorize_tool_call(req: AuthorizationRequest) -> AuthorizationResponse:
    """Evaluate whether an agent is authorized to call a specific tool."""
    ctx = CallContext(purpose=req.purpose)
    resource = ResourceSelector(
        account_scope=req.account_id,
        name_scope=req.capability,
    )
    t0 = time.perf_counter()
    decision = _middleware.authorize_call(
        principal_chain=[req.principal],
        action=Action.CALL,
        capability=req.capability,
        resource=resource,
        context=ctx,
    )
    latency_ms = (time.perf_counter() - t0) * 1000.0

    output = None
    if decision.allowed and req.capability in _tools:
        output = _tools[req.capability](req.query)

    return AuthorizationResponse(
        allowed=decision.allowed,
        reason_code=decision.reason_code,
        record_fingerprint=decision.record_fingerprint,
        obligations=[ob.value for ob in decision.obligations],
        output=output,
        latency_ms=latency_ms,
    )
