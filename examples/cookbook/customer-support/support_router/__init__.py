"""Customer Support Router — production mini-project.

Patterns  : Supervisor + TalkerReasoner + Human-in-the-Loop + BoundedExecution
Stack     : Blueprint YAML → Supervisor → TalkerReasoner (×3) → HumanInTheLoop →
            TraceEventBus + CostTracker + Recorder + JsonlExporter → FastAPI
Requires  : ANTHROPIC_API_KEY  OPENAI_API_KEY
            ZENDESK_URL  ZENDESK_EMAIL  ZENDESK_TOKEN
"""
__version__ = "1.0.0"
__all__ = ["build", "app"]

from .pipeline import build
from .api import app
