"""Code Review System — production mini-project.

Patterns  : CrossReflection + Pipeline + Human-in-the-Loop + BoundedExecution
Stack     : Blueprint YAML → CrossReflection → Pipeline → HumanInTheLoop →
            TraceEventBus + CostTracker + Recorder + JsonlExporter → FastAPI
Requires  : ANTHROPIC_API_KEY  OPENAI_API_KEY
            REVIEW_QUEUE_URL  REVIEW_QUEUE_TOKEN
"""
__version__ = "1.0.0"
__all__ = ["build", "app"]

from .pipeline import build
from .api import app
