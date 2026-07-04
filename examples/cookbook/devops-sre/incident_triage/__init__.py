"""Incident Triage Pipeline — production mini-project.

Patterns  : Pipeline + Human-in-the-Loop + BoundedExecution
Stack     : Blueprint YAML → Pipeline → HumanInTheLoop →
            TraceEventBus + CostTracker + Recorder + JsonlExporter → FastAPI
Requires  : ANTHROPIC_API_KEY  OPENAI_API_KEY
            PAGERDUTY_ROUTING_KEY  PAGERDUTY_API_KEY
"""
__version__ = "1.0.0"
__all__ = ["build", "app"]

from .pipeline import build
from .api import app
