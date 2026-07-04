"""Research Assistant — production mini-project.

Patterns  : FanOutFanIn + Debate + Pipeline + ReAct + BoundedExecution
Stack     : Blueprint YAML → FanOutFanIn → Debate → Pipeline →
            TraceEventBus + CostTracker + Recorder + JsonlExporter → FastAPI
Requires  : ANTHROPIC_API_KEY  OPENAI_API_KEY
"""
__version__ = "1.0.0"
__all__ = ["build", "app"]

from .pipeline import build
from .api import app
