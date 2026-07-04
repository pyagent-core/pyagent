"""Loan Underwriting Committee — production mini-project.

Patterns  : Debate
Stack     : Blueprint YAML → Debate → BoundedExecution →
            TraceEventBus + CostTracker + Recorder + JsonlExporter → FastAPI
Requires  : ANTHROPIC_API_KEY  GEMINI_API_KEY
"""
__version__ = "1.0.0"
__all__ = ["build", "app"]

from .pipeline import build
from .api import app
