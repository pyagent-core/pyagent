"""AML Transaction Monitoring — production mini-project.

Patterns  : Pipeline + Human-in-the-Loop
Stack     : Blueprint YAML → Pipeline → BoundedExecution →
            TraceEventBus + CostTracker + Recorder + JsonlExporter → FastAPI
Requires  : ANTHROPIC_API_KEY  OPENAI_API_KEY
            COMPLIANCE_API_URL  COMPLIANCE_API_KEY
"""
__version__ = "1.0.0"
__all__ = ["build", "app"]

from .pipeline import build
from .api import app
