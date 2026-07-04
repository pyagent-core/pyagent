"""Emergent NPC World — production mini-project.

Patterns  : Blackboard + BoundedExecution
Requires  : OPENAI_API_KEY
"""
__version__ = "1.0.0"
__all__ = ["build", "app"]
from .pipeline import build
from .api import app
