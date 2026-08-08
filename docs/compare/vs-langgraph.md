---
description: "pyagent-blueprint vs. LangGraph — a grounded comparison of declaring a supervisor workflow as YAML compiled to a real StateGraph, versus hand-writing the graph in Python."
---

# pyagent-blueprint vs. LangGraph

LangGraph models a multi-agent system as an explicit `StateGraph`: nodes, edges, and a shared state
object, all wired in Python. `pyagent-blueprint`'s `langgraph` adapter compiles a YAML manifest into
that exact same `StateGraph` API — so the comparison isn't "YAML vs. LangGraph," it's "author your
graph as a manifest vs. author it as code," while both ultimately execute the identical LangGraph
runtime.

This is a real, verified adapter — not an aspirational one. `pip install "pyagent-blueprint[langgraph]"`
gets you the `langgraph` adapter, whose `compile()` builds a genuine `langgraph.graph.StateGraph`,
calling `add_node()`/`add_edge()` for each agent in the workflow and compiling it with LangGraph's
own `.compile()`; `run()` invokes it via the
real `ainvoke()` path. It's certified against the same `AdapterConformanceSuite` every other adapter
must pass.

## Same pipeline, two authoring styles

**Hand-written LangGraph:**

```python
from langgraph.graph import END, START, StateGraph
from typing import TypedDict

class GraphState(TypedDict):
    input: str
    output: str

def researcher_node(state: GraphState) -> GraphState:
    # call your LLM here
    return {"output": "research summary"}

def writer_node(state: GraphState) -> GraphState:
    return {"output": "final draft"}

graph = StateGraph(GraphState)
graph.add_node("researcher", researcher_node)
graph.add_node("writer", writer_node)
graph.add_edge(START, "researcher")
graph.add_edge("researcher", "writer")
graph.add_edge("writer", END)
app = graph.compile()
```

**Equivalent `pyagent-blueprint` manifest:**

```yaml
api_version: pyagent/v1
metadata:
  name: research-pipeline
  version: 1.0.0
providers:
  primary:
    model: gpt-4.1-mini
agents:
  researcher:
    prompt: "Research the topic and produce a summary"
    provider: primary
  writer:
    prompt: "Turn the research summary into a final draft"
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

spec = load_blueprint("research-pipeline.yaml")
ir = BlueprintIR.from_spec(spec)
adapter = AdapterRegistry.discover()["langgraph"]()
artifact = adapter.compile(ir)              # a real langgraph.graph.StateGraph, compiled
result = await adapter.run(artifact, workflow="pipeline", input_="multi-agent orchestration trends")
```

Both produce the same `StateGraph` shape under the hood. The manifest version adds: static
validation (`pyagent-blueprint validate research-pipeline.yaml`) before any node runs, a semantic
diff (`pyagent-blueprint diff old.yaml new.yaml`) between versions, and a stable diagnostic if a
declared governance feature (a budget, an SLA, a memory tier) has no LangGraph-side equivalent yet —
rather than that feature being silently ignored by hand-written code.

## Where LangGraph is still the better fit

If your control flow needs genuinely dynamic graph construction at runtime — nodes and edges decided
by the output of a previous step, not knowable ahead of time — write it directly in LangGraph.
Blueprint's IR models a declared, typed workflow; it does not attempt to express arbitrary runtime
graph mutation. The adapter targets the common case (named patterns compiled to a static graph
shape), not LangGraph's full expressiveness.

## Migrating an existing LangGraph app

There is no dedicated LangGraph→Blueprint migration guide yet — this is intentionally sequenced
behind the Agent Spec interop bridge (Step 8 of the engineering roadmap), so that migration guidance
can point at a real, lossless import path rather than a manual rewrite. Until then, the pattern above
— re-declaring an existing graph's nodes as `agents:` and its edges as a `pipeline`/`supervisor`/etc.
workflow — is the direct manual route.
