"""CV Screener — production mini-project.

Patterns  : Fan-Out/Fan-In + Guardrails + BoundedExecution
Stack     : Blueprint YAML → FanOutFanIn → BoundedExecution →
            TraceEventBus + CostTracker + Recorder + JsonlExporter → FastAPI
Requires  : ANTHROPIC_API_KEY  OPENAI_API_KEY
"""
__version__ = "1.0.0"
__all__ = ["build", "app"]

from .pipeline import build
from .api import app
