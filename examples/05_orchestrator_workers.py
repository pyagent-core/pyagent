"""Example: Orchestrator-Workers — dynamic task delegation."""

import asyncio

from pyagent_patterns.base import Agent, MockLLM
from pyagent_patterns.orchestration import OrchestratorWorkers


async def main():
    orch_llm = MockLLM(responses=[
        '{"assignments": [{"worker": "researcher", "subtask": "Find AI trends data"}]}',
        "Final: AI essay synthesized from research",
    ])
    worker_llm = MockLLM(responses=["Found: Transformers dominate NLP, diffusion models for images"])

    ow = OrchestratorWorkers(
        orchestrator=Agent("orchestrator", orch_llm),
        workers=[
            Agent("researcher", worker_llm, description="Finds and summarizes info"),
            Agent("writer", worker_llm, description="Writes prose"),
        ],
    )
    result = await ow.run("Write a short essay on AI trends")
    print(f"Output: {result.output}")
    print(f"Workers used: {result.metadata['workers_used']}")

if __name__ == "__main__":
    asyncio.run(main())
