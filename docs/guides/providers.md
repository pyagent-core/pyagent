# Providers Guide

Multi-provider abstraction layer for LLM applications — register, route, negotiate, and optimize across providers.

## Overview

`pyagent-providers` gives you a unified interface for working with multiple LLM providers (OpenAI, Anthropic, local models, etc.) through a single `ProviderProtocol`.

## Key Concepts

### ProviderProtocol

Every provider implements this protocol:

```python
from pyagent_providers import ProviderProtocol

class MyProvider(ProviderProtocol):
    async def complete(self, messages, **kwargs) -> CompletionResult: ...
    async def health_check(self) -> HealthStatus: ...
    def capabilities(self) -> ProviderCapabilities: ...
```

### ProviderRegistry

Central registry for named providers:

```python
from pyagent_providers import ProviderRegistry, MockProvider

registry = ProviderRegistry()
registry.register("primary", MockProvider(name="gpt-4o", model="gpt-4o"))
registry.register("fallback", MockProvider(name="gpt-mini", model="gpt-4o-mini"))

provider = registry.get("primary")
```

### ProviderRouter

Route requests based on strategies:

| Strategy | Description |
|----------|-------------|
| `capability_first` | Pick first provider matching required capabilities |
| `cost_first` | Pick cheapest provider |
| `latency_first` | Pick lowest-latency provider |
| `round_robin` | Rotate across providers |

```python
from pyagent_providers import ProviderRouter

router = ProviderRouter(registry, strategy="cost_first")
result = await router.route(messages, required_capabilities=["streaming"])
```

### FallbackChain

Resilient completion with automatic failover:

```python
from pyagent_providers import FallbackChain

chain = FallbackChain(providers=[primary, secondary, tertiary])
result = await chain.complete(messages)
# Automatically tries next provider on failure
```

### CapabilityNegotiator

Find providers matching specific capabilities:

```python
from pyagent_providers import CapabilityNegotiator

negotiator = CapabilityNegotiator(registry)
matches = negotiator.find(required=["function_calling", "streaming"])
```

### CostOptimizer

Compare costs across providers for a given workload:

```python
from pyagent_providers import CostOptimizer

optimizer = CostOptimizer(registry)
ranked = optimizer.rank_by_cost(prompt_tokens=1000, completion_tokens=500)
```

## Integration with Blueprint

In a blueprint YAML, providers are declared and referenced by agents:

```yaml
providers:
  primary:
    model: gpt-4o
  fallback:
    model: gpt-4o-mini

agents:
  classifier:
    prompt: "Classify the input"
    provider: primary
```

The `BlueprintCompiler` resolves these references through the `ProviderRegistry`.

## API Reference

::: pyagent_providers
