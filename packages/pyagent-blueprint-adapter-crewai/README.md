# pyagent-blueprint-adapter-crewai

A [pyagent-blueprint](https://pyagent.org) `RuntimeAdapter` targeting **CrewAI**.

Published separately from `pyagent-blueprint` core so CrewAI's release
cadence never destabilizes core CI. Self-certifies against the shared
`AdapterConformanceSuite`.

## Install

```bash
pip install -e .[test]
```

## Model

Each blueprint workflow compiles to a role-based CrewAI `Crew`: one
`Agent` + one `Task` per referenced agent (ref order), executed via
`Process.sequential` — CrewAI's built-in task-context chaining feeds
each task's output into the next. Each `Agent` is bound to a
deterministic offline `BaseLLM` subclass (no API key needed), so the
adapter exercises CrewAI's real `Crew.kickoff()` execution engine.

This is a third structurally distinct proof point (after LangGraph's
declared graph and the OpenAI Agents SDK's handoff/turn model): CrewAI
is role-based (`role`/`goal`/`backstory` + task descriptions).

## Test

```bash
pytest tests/
```
