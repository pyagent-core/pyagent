"""Provider adapters — concrete implementations of ProviderProtocol."""

from pyagent_providers.adapters.mock import MockProvider

__all__ = ["MockProvider"]

# Optional adapters — import fails gracefully if deps not installed
try:
    from pyagent_providers.adapters.openai import OpenAIProvider  # noqa: F401

    __all__.append("OpenAIProvider")
except ImportError:
    pass

try:
    from pyagent_providers.adapters.anthropic import AnthropicProvider  # noqa: F401

    __all__.append("AnthropicProvider")
except ImportError:
    pass

try:
    from pyagent_providers.adapters.litellm import LiteLLMProvider  # noqa: F401

    __all__.append("LiteLLMProvider")
except ImportError:
    pass
