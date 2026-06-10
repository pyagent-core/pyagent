# pyagent-providers

**Multi-provider abstraction with capability negotiation, health checks, fallback chains, and cost-optimized routing** for multi-agent LLM systems. Drop-in replacement for hardcoded model specs.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](../../LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

## Install

```bash
pip install pyagent-providers                  # Core (includes MockProvider)
pip install pyagent-providers[openai]          # + OpenAI adapter
pip install pyagent-providers[anthropic]       # + Anthropic adapter
pip install pyagent-providers[litellm]         # + LiteLLM (100+ models)
pip install pyagent-providers[all]             # All adapters
```

Depends on: `pyagent-patterns`, `pyagent-router`.

## Why Provider Abstraction?

Without `pyagent-providers`, switching models means rewriting LLM wrappers. With it, your agents talk to a `ProviderProtocol` that satisfies the existing `LLMCallable` interface — so every provider is a drop-in replacement for `Agent.llm`.

```python
from pyagent_patterns.base import Agent
from pyagent_providers.adapters.mock import MockProvider

# Any provider works as an Agent's LLM
provider = MockProvider(name="test", responses=["Hello"])
agent = Agent("greeter", provider)  # provider satisfies LLMCallable
```

## ProviderProtocol — The Interface

Every provider implements this:

```python
from pyagent_providers import ProviderProtocol, HealthStatus, ProviderCapabilities

class MyCustomProvider:
    @property
    def name(self) -> str:
        return "my_provider"

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            models=["my-model-small", "my-model-large"],
            capabilities={Capability.GENERAL, Capability.CODE},
            max_context=128_000,
            supports_streaming=True,
        )

    async def health(self) -> HealthStatus:
        # check your endpoint
        return HealthStatus.HEALTHY

    async def complete(self, messages, model=None) -> str:
        # call your API
        return "response"

    async def __call__(self, messages) -> str:
        return await self.complete(messages)
```

## ProviderRegistry — Register and Discover

```python
import asyncio
from pyagent_providers import ProviderRegistry, HealthStatus
from pyagent_providers.adapters.mock import MockProvider
from pyagent_router.selector import Capability

registry = ProviderRegistry()

async def setup():
    await registry.register(MockProvider(
        name="openai",
        models=["gpt-4o-mini", "gpt-4o"],
        capabilities={Capability.GENERAL, Capability.CODE, Capability.VISION},
    ))
    await registry.register(MockProvider(
        name="anthropic",
        models=["claude-haiku-3.5", "claude-sonnet-4"],
        capabilities={Capability.GENERAL, Capability.CODE, Capability.CREATIVE},
    ))

    # Discover by capability
    coders = registry.discover({Capability.CODE})
    print([p.name for p in coders])  # ["openai", "anthropic"]

    vision = registry.discover({Capability.VISION})
    print([p.name for p in vision])  # ["openai"]

    # Health check all
    statuses = await registry.check_health()
    print(statuses)  # {"openai": "healthy", "anthropic": "healthy"}

    # Remove unhealthy
    removed = await registry.remove_unhealthy()
    print(f"Removed: {removed}")  # []

asyncio.run(setup())
```

## ProviderRouter — Strategy-Based Routing

Four strategies: `CAPABILITY_FIRST`, `COST_FIRST`, `LATENCY_FIRST`, `ROUND_ROBIN`.

```python
from pyagent_providers import ProviderRouter, RoutingStrategy
from pyagent_patterns.base import Message

# Capability-first (default): pick the provider with broadest capabilities
router = ProviderRouter(registry, strategy=RoutingStrategy.CAPABILITY_FIRST)
provider, model = asyncio.run(router.route(
    [Message.user("Write a Python REST API with FastAPI")],
    required={Capability.CODE},
))
print(f"{provider.name}/{model}")

# Cost-first: cheapest provider + model for the task
router = ProviderRouter(registry, strategy=RoutingStrategy.COST_FIRST)
provider, model = asyncio.run(router.route([Message.user("What is 2+2?")]))
print(f"{provider.name}/{model}")  # picks gpt-4.1-nano

# Round-robin: cycle through providers for load distribution
router = ProviderRouter(registry, strategy=RoutingStrategy.ROUND_ROBIN)
for _ in range(4):
    provider, model = asyncio.run(router.route([Message.user("Balance me")]))
    print(provider.name, end=" ")
# openai anthropic openai anthropic
```

## FallbackChain — Resilient Completion

Try providers in order. If one fails, fall through to the next. Optionally integrates with `CircuitBreaker` from `pyagent-patterns`.

```python
from pyagent_providers import FallbackChain

chain = FallbackChain(providers=[
    primary_openai,      # try first
    fallback_anthropic,  # if OpenAI fails
    emergency_litellm,   # last resort
])

result = asyncio.run(chain.complete([Message.user("Important task")]))
print(result.output)           # response from first successful provider
print(result.provider_name)    # which provider answered
print(result.attempts)         # full attempt log with errors

# With circuit breaker integration
from pyagent_patterns.recovery import CircuitBreaker

chain = FallbackChain(
    providers=[primary, fallback],
    circuit_breakers={
        "primary": CircuitBreaker(failure_threshold=3, reset_timeout_seconds=60),
    },
)
```

## CapabilityNegotiator — Match Task Requirements

Scores providers by capability overlap, context window, and feature support.

```python
from pyagent_providers import CapabilityNegotiator

negotiator = CapabilityNegotiator(registry)

# Find best provider for code + reasoning tasks
result = negotiator.negotiate(
    required_capabilities={Capability.CODE, Capability.REASONING},
    min_context=100_000,
)
if result:
    print(result.provider.name)         # "openai" or "anthropic"
    print(result.model)                 # best model from that provider
    print(f"Match: {result.match_score:.0%}")
    print(result.matched_capabilities)  # {CODE, REASONING}
    print(result.missing_capabilities)  # set()

# Get all ranked matches
all_matches = negotiator.negotiate_all(
    required_capabilities={Capability.GENERAL},
    limit=5,
)
for m in all_matches:
    print(f"  {m.provider.name}: {m.match_score:.0%}")
```

## CostOptimizer — Multi-Provider Cost Comparison

```python
from pyagent_providers import CostOptimizer

optimizer = CostOptimizer(registry)

# Compare all providers for a task
estimates = optimizer.compare("Explain distributed consensus algorithms")
for est in estimates[:5]:
    print(f"{est.provider_name}/{est.model}: ${est.estimate.total_cost:.7f}")

# Get cheapest option
cheapest = optimizer.cheapest("Simple greeting task")
if cheapest:
    print(f"Use {cheapest.provider_name}/{cheapest.model}: ${cheapest.estimate.total_cost:.7f}")

# Get provider object + model for direct use
pair = optimizer.cheapest_provider("My task")
if pair:
    provider, model = pair
    agent = Agent("my_agent", provider)
```

## Adapter Examples

### OpenAI

```python
from pyagent_providers.adapters.openai import OpenAIProvider

openai = OpenAIProvider(
    api_key="sk-...",            # or set OPENAI_API_KEY env var
    default_model="gpt-4o-mini",
    models=["gpt-4o-mini", "gpt-4o", "o3-mini"],
)

await registry.register(openai)
result = await openai.complete([Message.user("Hello")])
```

### Anthropic

```python
from pyagent_providers.adapters.anthropic import AnthropicProvider

anthropic = AnthropicProvider(
    api_key="sk-ant-...",
    default_model="claude-sonnet-4-20250514",
)

await registry.register(anthropic)
result = await anthropic.complete([Message.user("Hello")])
```

### LiteLLM (100+ Providers)

```python
from pyagent_providers.adapters.litellm import LiteLLMProvider

litellm = LiteLLMProvider(
    models=["gpt-4o-mini", "anthropic/claude-haiku-3.5", "gemini/gemini-2.5-flash"],
    default_model="gpt-4o-mini",
)

await registry.register(litellm)
result = await litellm.complete([Message.user("Hello")], model="gemini/gemini-2.5-flash")
```

### MockProvider (Testing)

```python
from pyagent_providers.adapters.mock import MockProvider

mock = MockProvider(
    name="test",
    responses=["Response 1", "Response 2"],
    models=["mock-fast", "mock-smart"],
    capabilities={Capability.GENERAL, Capability.CODE},
    health_status=HealthStatus.HEALTHY,
)

await registry.register(mock)
result = await mock.complete([Message.user("Test")])
print(mock.call_count)  # 1
```

## Integration with pyagent-patterns

```python
from pyagent_patterns.base import Agent
from pyagent_patterns.orchestration import Pipeline
from pyagent_providers import ProviderRegistry, CapabilityNegotiator
from pyagent_providers.adapters.mock import MockProvider

# Set up providers
registry = ProviderRegistry()
registry.register_sync(MockProvider(name="fast", responses=["Extracted facts"]))
registry.register_sync(MockProvider(name="smart", responses=["Detailed analysis"]))

# Use providers as Agent LLMs
fast = registry.get("fast")
smart = registry.get("smart")

pipeline = Pipeline(stages=[
    Agent("extractor", fast, system_prompt="Extract key facts."),
    Agent("analyst", smart, system_prompt="Analyse in depth."),
])

result = asyncio.run(pipeline.run("Process this document"))
print(result.output)
```

## Full Documentation

See [pyagent.dev](https://pyagent.dev) for full API reference and integration guides.
