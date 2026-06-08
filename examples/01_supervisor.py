"""Example: Supervisor — route customer queries to specialists."""

import asyncio

from pyagent_patterns.base import Agent, MockLLM
from pyagent_patterns.orchestration import Supervisor


async def main():
    supervisor = Supervisor(
        classifier=Agent("classifier", MockLLM(responses=["billing"])),
        routes={
            "billing": Agent(
                "billing", MockLLM(responses=["Your refund of $50 has been processed."])
            ),
            "tech": Agent("tech", MockLLM(responses=["Please restart your device."])),
        },
    )
    result = await supervisor.run("I need a refund for my last order")
    print(f"Output: {result.output}")
    print(f"Route: {result.metadata['route_key']}")
    print(f"Duration: {result.duration_seconds:.3f}s")


if __name__ == "__main__":
    asyncio.run(main())
