"""Robo-Advisor Onboarding — production mini-project.

Patterns  : Role-Based
Stack     : Blueprint YAML → RoleBased → BoundedExecution →
            TraceEventBus + CostTracker + Recorder + JsonlExporter → FastAPI
Requires  : ANTHROPIC_API_KEY  OPENAI_API_KEY
"""
__version__ = "1.0.0"
__all__ = ["build", "app"]

from .pipeline import build
from .api import app
