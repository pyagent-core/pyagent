"""Portfolio Review — production mini-project.

Patterns  : Supervisor + Evaluator-Optimizer
Stack     : Blueprint YAML → Supervisor → EvaluatorOptimizer → BoundedExecution →
            TraceEventBus + CostTracker + Recorder + JsonlExporter → FastAPI
Requires  : ANTHROPIC_API_KEY
"""
__version__ = "1.0.0"
__all__ = ["build", "app"]

from .pipeline import build
from .api import app
