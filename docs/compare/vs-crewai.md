---
description: "pyagent-blueprint vs. CrewAI — comparing a role-based Crew defined in Python against the same crew declared as a YAML manifest and compiled to CrewAI's real Agent/Task/Crew execution engine."
---

# pyagent-blueprint vs. CrewAI

CrewAI models a multi-agent system as a `Crew`: a list of role-based `Agent`s (`role`/`goal`/
`backstory`), each paired with a `Task`, run through a `Process` (sequential or hierarchical).
`pyagent-blueprint`'s `crewai` adapter compiles a YAML manifest directly into that same `Agent`/
`Task`/`Crew` structure — the comparison is about where the role/goal/task wiring lives, not about
replacing CrewAI's execution engine.

This is a real, verified adapter. `pyagent-blueprint-adapter-crewai`'s `compile()` builds actual
CrewAI `Agent(role=..., goal=..., backstory=...)` and `Task(description=..., agent=...)` objects for
every agent in a workflow, assembles them into a real `Crew(agents=..., tasks=..., process=
Process.sequential)`, and `run()` calls CrewAI's own `crew.kickoff_async()`. It passes the same
`AdapterConformanceSuite` as every other adapter.

## Same crew, two authoring styles

**Hand-written CrewAI:**

```python
from crewai import Agent, Task, Crew, Process

researcher = Agent(
    role="researcher",
    goal="Research the topic and produce a summary",
    backstory="An analyst who synthesizes sources quickly",
)
writer = Agent(
    role="writer",
    goal="Turn the research summary into a final draft",
    backstory="A writer who turns notes into polished prose",
)
research_task = Task(description="{input}", expected_output="A research summary", agent=researcher)
write_task = Task(description="Continue based on the research for: {input}",
                   expected_output="A final draft", agent=writer)

crew = Crew(agents=[researcher, writer], tasks=[research_task, write_task], process=Process.sequential)
result = crew.kickoff(inputs={"input": "multi-agent orchestration trends"})
```

**Equivalent `pyagent-blueprint` manifest:**

```yaml
api_version: pyagent/v1
metadata:
  name: research-crew
  version: 1.0.0
providers:
  primary:
    model: gpt-4.1-mini
agents:
  researcher:
    prompt: "Research the topic and produce a summary"
    description: "An analyst who synthesizes sources quickly"
    provider: primary
  writer:
    prompt: "Turn the research summary into a final draft"
    description: "A writer who turns notes into polished prose"
    provider: primary
workflows:
  pipeline:
    pattern: pipeline
    agents:
      stages: [researcher, writer]
```

```python
from pyagent_blueprint.adapter import AdapterRegistry
from pyagent_blueprint.ir import BlueprintIR
from pyagent_blueprint.loader import load_blueprint

spec = load_blueprint("research-crew.yaml")
ir = BlueprintIR.from_spec(spec)
adapter = AdapterRegistry.discover()["crewai"]()
artifact = adapter.compile(ir)              # real CrewAI Agent/Task/Crew objects
result = await adapter.run(artifact, workflow="pipeline", input_="multi-agent orchestration trends")
```

The manifest's `agents.<name>.description` maps to CrewAI's `backstory`; `prompt` maps to `goal`.
Both ultimately run the identical `Crew.kickoff_async()` path.

## Where CrewAI is still the better fit

CrewAI's role-based framing (`role`/`goal`/`backstory`) and its hierarchical process mode carry
nuance that a declarative manifest doesn't try to fully capture yet — if you're leaning heavily on
CrewAI-specific features like custom tools per agent or its hierarchical manager process, writing
directly against CrewAI's SDK gives you the full surface area. The adapter targets the patterns
`pyagent-blueprint` already models (pipeline, supervisor, orchestrator-workers, etc.), compiled onto
CrewAI's sequential process.

## Migrating an existing CrewAI app

As with LangGraph, a dedicated CrewAI→Blueprint migration guide is sequenced behind the Agent Spec
interop bridge so it can describe a real import path rather than a manual rewrite. Until then, map
each `Agent`'s `role`/`goal`/`backstory` to a Blueprint `agents:` entry and each `Task` ordering to a
`workflows:` pattern (`pipeline` for sequential tasks, `supervisor` for role-based dispatch).
