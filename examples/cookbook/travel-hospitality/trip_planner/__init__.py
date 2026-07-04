"""Trip-Planning Swarm — production mini-project.

Patterns  : Swarm + BoundedExecution
Requires  : GEMINI_API_KEY
"""
__version__ = "1.0.0"
__all__ = ["build", "app"]
from .pipeline import build
from .api import app
