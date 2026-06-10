"""PyAgent Providers — multi-provider abstraction with capability negotiation and fallback chains."""

from pyagent_providers.base import (
    HealthStatus,
    ProviderCapabilities,
    ProviderInfo,
    ProviderProtocol,
)
from pyagent_providers.cost import CostOptimizer, ProviderCostEstimate
from pyagent_providers.fallback import FallbackChain, FallbackResult
from pyagent_providers.negotiation import CapabilityNegotiator, NegotiationResult
from pyagent_providers.registry import ProviderRegistry
from pyagent_providers.router import ProviderRouter, RoutingStrategy

__all__ = [
    "CapabilityNegotiator",
    "CostOptimizer",
    "FallbackChain",
    "FallbackResult",
    "HealthStatus",
    "NegotiationResult",
    "ProviderCapabilities",
    "ProviderCostEstimate",
    "ProviderInfo",
    "ProviderProtocol",
    "ProviderRegistry",
    "ProviderRouter",
    "RoutingStrategy",
]
__version__ = "0.1.0"
