"""Example 26: Multi-provider setup with fallback chain.

Demonstrates:
- Creating a ProviderRegistry with multiple providers
- Configuring a FallbackChain for resilient completions
- Using CapabilityNegotiator to find providers by capability
- CostOptimizer for comparing provider costs
"""

import asyncio

from pyagent_providers import (
    FallbackChain,
    MockProvider,
    ProviderRegistry,
)


async def main() -> None:
    # Register providers
    registry = ProviderRegistry()
    primary = MockProvider(name="gpt-4o", model="gpt-4o")
    fallback = MockProvider(name="gpt-4o-mini", model="gpt-4o-mini")

    registry.register("primary", primary)
    registry.register("fallback", fallback)

    print("Registered providers:", registry.list_providers())

    # FallbackChain: try primary, fall back to secondary
    chain = FallbackChain(providers=[primary, fallback])
    result = await chain.complete([{"role": "user", "content": "Hello!"}])
    print(f"Output: {result.text}")
    print(f"Provider used: {result.provider_name}")

    # Health check
    for name in registry.list_providers():
        provider = registry.get(name)
        health = await provider.health_check()
        print(f"  {name}: {health}")


if __name__ == "__main__":
    asyncio.run(main())
