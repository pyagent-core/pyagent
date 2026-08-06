# pyagent-blueprint-adapter-langgraph

A [pyagent-blueprint](https://pyagent.org) `RuntimeAdapter` targeting **LangGraph**.

Published separately from `pyagent-blueprint` core so LangGraph's release
cadence and breaking changes never destabilize core CI (see
TRANSFORMATION-PLAN.md Section 9). Self-certifies against the shared
`AdapterConformanceSuite`.

## Install

```bash
pip install -e .[test]
```

## Model

Each blueprint workflow compiles to a real LangGraph `StateGraph`: one
node per referenced agent, wired `START -> agent_1 -> ... -> agent_n -> END`.
Node bodies use a deterministic mock call (no API key needed), so this
adapter is fully testable offline — the proof point is that the
`RuntimeAdapter` contract maps cleanly onto LangGraph's real
graph-compilation/execution engine (`StateGraph`, `.compile()`,
`.ainvoke()`, `.astream()`), not a production LLM integration.

Declares `Capability.STREAMING`, backed by LangGraph's native `.astream()`.

## Test

```bash
pytest tests/
```
