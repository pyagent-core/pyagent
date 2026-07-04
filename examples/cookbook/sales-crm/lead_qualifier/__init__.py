"""Lead Qualifier — production mini-project.

Patterns  : Supervisor + Pipeline + BoundedExecution
Requires  : ANTHROPIC_API_KEY  OPENAI_API_KEY
"""
__version__ = "1.0.0"
__all__ = ["build", "app"]
from .pipeline import build
from .api import app
