"""Example: Layered Cooperation — multi-level analysis."""

import asyncio

from pyagent_patterns.base import Agent, MockLLM
from pyagent_patterns.structural import Layered
from pyagent_patterns.structural.layered import Layer

async def main():
    llm = MockLLM(responses=["Raw data gathered", "Analyzed patterns", "Executive summary"])
    pattern = Layered(layers=[
        Layer(name="gather", agents=[Agent("scraper", llm)]),
        Layer(name="analyze", agents=[Agent("analyst", llm)]),
        Layer(name="synthesize", agents=[Agent("exec", llm)]),
    ])
    result = await pattern.run("Analyze competitive landscape")
    print(f"Output: {result.output}")
    print(f"Layers: {result.metadata['layer_count']}")

if __name__ == "__main__":
    asyncio.run(main())
