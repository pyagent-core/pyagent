"""Example 28: Load YAML blueprint → compile → run.

Demonstrates:
- Loading a blueprint from YAML
- Compiling to a RuntimeGraph
- Running a workflow with MockLLM
- Inspecting the compiled graph
"""

import asyncio

from pyagent_blueprint import BlueprintCompiler, load_blueprint_from_str


BLUEPRINT_YAML = """
api_version: pyagent/v1
metadata:
  name: research-pipeline
  version: 1.0.0
  description: Two-stage research with review

providers:
  primary:
    model: gpt-4o

agents:
  researcher:
    prompt: "Research the given topic thoroughly"
    provider: primary
  reviewer:
    prompt: "Review and improve the research output"
    provider: primary

workflows:
  research:
    pattern: pipeline
    agents:
      stages:
        researcher: researcher
        reviewer: reviewer
"""


async def main() -> None:
    # Load from YAML string
    spec = load_blueprint_from_str(BLUEPRINT_YAML)
    print(f"Loaded: {spec.metadata.name} v{spec.metadata.version}")
    print(f"Agents: {list(spec.agents.keys())}")
    print(f"Workflows: {list(spec.workflows.keys())}")

    # Compile
    compiler = BlueprintCompiler()
    graph = compiler.compile(spec)
    print(f"\nCompiled graph: {graph.describe()}")

    # Run
    result = await graph.run("research", "Explain the Transformer architecture")
    print(f"\nResult: {result.output[:200]}...")


if __name__ == "__main__":
    asyncio.run(main())
