"""Fraud Investigation Assistant — production mini-project.

Patterns  : ReAct + BoundedExecution
Stack     : Blueprint YAML → ReAct (with tools) →
            TraceEventBus + CostTracker + Recorder + JsonlExporter → FastAPI
Requires  : OPENAI_API_KEY
"""
__version__ = "1.0.0"
__all__ = ["build", "app"]

from .pipeline import build
from .api import app
