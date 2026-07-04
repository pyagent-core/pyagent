"""ESG Report Analyzer — production mini-project.

Patterns  : Orchestrator-Workers
Stack     : Blueprint YAML → OrchestratorWorkers → BoundedExecution →
            TraceEventBus + CostTracker + Recorder + JsonlExporter → FastAPI
Requires  : ANTHROPIC_API_KEY  OPENAI_API_KEY
"""
__version__ = "1.0.0"
__all__ = ["build", "app"]

from .pipeline import build
from .api import app
