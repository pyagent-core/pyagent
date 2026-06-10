"""PyAgent Studio — Kubernetes Dashboard for Agent Systems."""

from pyagent_studio.services.blueprint_service import BlueprintService
from pyagent_studio.services.governance_service import GovernanceService
from pyagent_studio.services.simulation_service import SimulationService
from pyagent_studio.services.trace_service import TraceService


# Lazy import for ProviderService (requires litellm)
def __getattr__(name: str):
    if name == "ProviderService":
        from pyagent_studio.services.provider_service import ProviderService

        return ProviderService
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "BlueprintService",
    "GovernanceService",
    "ProviderService",
    "SimulationService",
    "TraceService",
]
__version__ = "0.1.0"
