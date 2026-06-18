"""FastAPI application factory for the PyAgent Studio web dashboard."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from pyagent_studio.services.blueprint_service import BlueprintService
from pyagent_studio.web.routes import (
    agents,
    diff,
    docs,
    governance,
    overview,
    providers,
    simulate,
    traces,
    workflows,
)

if TYPE_CHECKING:
    from starlette.responses import Response

_WEB_DIR = Path(__file__).parent
_TEMPLATE_DIR = _WEB_DIR / "templates"
_STATIC_DIR = _WEB_DIR / "static"
_SAMPLE_BLUEPRINT = _WEB_DIR.parent / "data" / "sample_blueprint.yaml"


class _NoCacheStaticFiles(StaticFiles):
    """StaticFiles that disables browser caching.

    The dashboard is a local dev tool whose CSS/JS change frequently; without
    this, browsers serve stale assets after an edit until a manual hard refresh.
    """

    def file_response(self, *args: object, **kwargs: object) -> Response:
        resp = super().file_response(*args, **kwargs)  # type: ignore[arg-type]
        resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return resp


def create_app(
    trace_path: str | Path | None = None,
    blueprint_path: str | Path | None = None,
) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        trace_path: Optional path to a recorded trace JSONL file to preload
            on the Overview dashboard. Falls back to sample data when omitted.
        blueprint_path: Optional path to a blueprint YAML to load for the
            resource tabs. Falls back to a bundled sample blueprint when omitted.
    """
    app = FastAPI(title="PyAgent Studio", version="0.1.0")

    # Jinja2 templates
    templates = Jinja2Templates(directory=str(_TEMPLATE_DIR))
    app.state.templates = templates
    app.state.trace_path = trace_path

    # Blueprint: load the given path, else the bundled sample so the resource
    # tabs (Agents, Workflows, Governance, ...) are populated out of the box.
    using_sample = blueprint_path is None
    resolved = Path(blueprint_path) if blueprint_path else _SAMPLE_BLUEPRINT
    blueprint_service: BlueprintService | None = BlueprintService()
    try:
        blueprint_service.load(resolved)
    except Exception:
        blueprint_service = None
        using_sample = False
    app.state.blueprint_service = blueprint_service
    app.state.using_sample_blueprint = using_sample

    # Static files (no-cache so edits show up without a manual hard refresh)
    app.mount("/static", _NoCacheStaticFiles(directory=str(_STATIC_DIR)), name="static")

    # Register route modules
    app.include_router(overview.router)
    app.include_router(agents.router, prefix="/agents", tags=["agents"])
    app.include_router(workflows.router, prefix="/workflows", tags=["workflows"])
    app.include_router(simulate.router, prefix="/simulate", tags=["simulate"])
    app.include_router(traces.router, prefix="/traces", tags=["traces"])
    app.include_router(governance.router, prefix="/governance", tags=["governance"])
    app.include_router(providers.router, prefix="/providers", tags=["providers"])
    app.include_router(diff.router, prefix="/diff", tags=["diff"])
    app.include_router(docs.router, prefix="/docs", tags=["docs"])

    return app
