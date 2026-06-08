"""Example: Pipeline — sequential document processing."""

import asyncio

from pyagent_patterns.base import Agent, MockLLM
from pyagent_patterns.orchestration import Pipeline


async def main():
    llm = MockLLM(responses=[
        "Extracted: Revenue $94B, profit margin 23%, growth 15%",
        "Summary: Strong Q3 — $94B revenue (+15%), 23% margins",
        "Resumen: Q3 fuerte — $94B ingresos (+15%), márgenes del 23%",
    ])
    pipeline = Pipeline(stages=[
        Agent("extractor", llm, system_prompt="Extract key facts"),
        Agent("summarizer", llm, system_prompt="Summarize concisely"),
        Agent("translator", llm, system_prompt="Translate to Spanish"),
    ])
    result = await pipeline.run("Q3 earnings report: revenue was $94B...")
    print(f"Output: {result.output}")
    print(f"Stages: {result.metadata['stages']}")

if __name__ == "__main__":
    asyncio.run(main())
