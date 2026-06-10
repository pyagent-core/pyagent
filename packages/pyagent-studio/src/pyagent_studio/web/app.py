"""FastAPI application factory for the PyAgent Studio web dashboard."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

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

_WEB_DIR = Path(__file__).parent
_TEMPLATE_DIR = _WEB_DIR / "templates"
_STATIC_DIR = _WEB_DIR / "static"


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(title="PyAgent Studio", version="0.1.0")

    # Jinja2 templates
    templates = Jinja2Templates(directory=str(_TEMPLATE_DIR))
    app.state.templates = templates

    # Static files
    app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")

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
