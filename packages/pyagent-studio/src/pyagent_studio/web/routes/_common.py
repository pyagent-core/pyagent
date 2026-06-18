"""Shared helpers for web routes."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from fastapi import Request

    from pyagent_studio.services.blueprint_service import BlueprintService


def get_blueprint_service(request: Request) -> BlueprintService | None:
    """Return the app's loaded BlueprintService, or None if none loaded."""
    return getattr(request.app.state, "blueprint_service", None)


def base_context(request: Request) -> dict[str, Any]:
    """Common template context: blueprint presence and sample-data flag."""
    bp = get_blueprint_service(request)
    spec = bp.spec if bp else None
    return {
        "has_blueprint": spec is not None,
        "using_sample_blueprint": getattr(request.app.state, "using_sample_blueprint", False),
        "blueprint_name": spec.metadata.name if spec else None,
    }
