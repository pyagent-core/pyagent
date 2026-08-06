"""Shared plumbing for the zero-dependency reference adapters.

None of this is framework-specific — it's just agent-ref resolution and
governance-diagnostic reporting logic every one of the four reference
adapters needs identically, since none of them enforce ANY governance
feature (they're deliberately minimal, structurally dissimilar execution
engines — see TRANSFORMATION-PLAN.md Section 6).
"""

from __future__ import annotations

from pyagent_blueprint.adapter import CompileDiagnostic
from pyagent_blueprint.diagnostics import (
    BUDGET_UNSUPPORTED,
    CHECKPOINT_UNSUPPORTED,
    GUARDRAIL_UNSUPPORTED,
    MEMORY_TIER_UNSUPPORTED,
    RECOVERY_UNSUPPORTED,
    ROUTING_UNSUPPORTED,
    SLA_UNSUPPORTED,
)
from pyagent_blueprint.ir import BlueprintIR


def flatten_agent_refs(agents_config: dict) -> list[str]:
    """Resolve a workflow's `agents` mapping into an ordered list of
    agent-name strings, regardless of shape.

    Handles all three shapes seen in canonical fixtures:
    - ``{"agent": "solo"}`` -> ``["solo"]``
    - ``{"stages": {"first": "first", "second": "second"}}`` -> ``["first", "second"]``
    - ``{"stages": ["first", "second"]}`` -> ``["first", "second"]``
    """
    refs: list[str] = []

    def _add(value: object) -> None:
        if isinstance(value, str):
            refs.append(value)
        elif isinstance(value, dict):
            for v in value.values():
                _add(v)
        elif isinstance(value, (list, tuple)):
            for v in value:
                _add(v)

    for value in agents_config.values():
        _add(value)
    return refs


def mock_call(agent_name: str, prompt: str, input_: str) -> str:
    """Deterministic, dependency-free stand-in for an LLM call.

    Every reference adapter uses this instead of a real model client —
    the point of these adapters is to stress-test the `RuntimeAdapter`
    contract's *shape*, not to be usable in production.
    """
    return f"[{agent_name}] {input_}"


def diagnose_common_governance(ir: BlueprintIR) -> list[CompileDiagnostic]:
    """Report every governance feature declared in `ir` that none of the
    four zero-dependency reference adapters enforce.

    These adapters are deliberately minimal execution engines with no
    routing, budget, memory, guardrail, or recovery enforcement at all —
    but per the contract, that must be reported via diagnostics, never
    silently dropped.
    """
    diagnostics: list[CompileDiagnostic] = []

    for wf_name, wf in ir.workflows.items():
        if wf.recovery is not None:
            diagnostics.append(
                CompileDiagnostic(
                    code=RECOVERY_UNSUPPORTED,
                    path=f"workflows.{wf_name}.recovery",
                    detail="This adapter has no retry/backoff/fallback enforcement.",
                )
            )
        if wf.guardrails:
            diagnostics.append(
                CompileDiagnostic(
                    code=GUARDRAIL_UNSUPPORTED,
                    path=f"workflows.{wf_name}.guardrails",
                    detail=f"Guardrails {list(wf.guardrails)} declared but not enforced.",
                )
            )
        if wf.config.get("human_in_the_loop"):
            diagnostics.append(
                CompileDiagnostic(
                    code=CHECKPOINT_UNSUPPORTED,
                    path=f"workflows.{wf_name}.config.human_in_the_loop",
                    detail="Workflow-level human-in-the-loop checkpoint is not enforced by this adapter.",
                )
            )

    for wf_name, contract in ir.contracts.items():
        diagnostics.append(
            CompileDiagnostic(
                code=SLA_UNSUPPORTED,
                path=f"contracts.{wf_name}.sla",
                detail="SLA (latency/cost/quality) is not enforced by this adapter.",
            )
        )
        if contract.sla.cost_max_usd:
            diagnostics.append(
                CompileDiagnostic(
                    code=BUDGET_UNSUPPORTED,
                    path=f"contracts.{wf_name}.sla.cost_max_usd",
                    detail="Cost budget is not enforced by this adapter.",
                )
            )

    if ir.memory is not None:
        diagnostics.append(
            CompileDiagnostic(
                code=MEMORY_TIER_UNSUPPORTED,
                path="memory",
                detail="Memory/context policy (tiers, compression, redaction) is not enforced by this adapter.",
            )
        )

    for agent_name, agent in ir.agents.items():
        if agent.guardrails:
            diagnostics.append(
                CompileDiagnostic(
                    code=GUARDRAIL_UNSUPPORTED,
                    path=f"agents.{agent_name}.guardrails",
                    detail=f"Guardrails {list(agent.guardrails)} declared but not enforced.",
                )
            )

    if any(p.fallback_ref for p in ir.providers.values()):
        diagnostics.append(
            CompileDiagnostic(
                code=ROUTING_UNSUPPORTED,
                path="providers",
                detail="Provider fallback/routing is not enforced by this adapter.",
            )
        )

    return diagnostics
