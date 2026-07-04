"""Earnings Call Analyzer — production mini-project.

Patterns  : Self-Reflection
Stack     : Blueprint YAML → SelfReflection → BoundedExecution →
            TraceEventBus + CostTracker + Recorder + JsonlExporter → FastAPI
Requires  : ANTHROPIC_API_KEY
"""
__version__ = "1.0.0"
__all__ = ["build", "app"]

from .pipeline import build
from .api import app
