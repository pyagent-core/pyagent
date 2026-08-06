# pyagent-blueprint-adapter-openai-agents

A [pyagent-blueprint](https://pyagent.org) `RuntimeAdapter` targeting the
**OpenAI Agents SDK**.

Published separately from `pyagent-blueprint` core so this SDK's release
cadence never destabilizes core CI. Self-certifies against the shared
`AdapterConformanceSuite`.

## Install

```bash
pip install -e .[test]
```

## Model

Each blueprint workflow compiles to a chain of OpenAI Agents SDK `Agent`
instances (one per referenced agent, in ref order), executed in sequence
via `Runner.run()` — output of each agent becomes the next agent's input.
Each `Agent` is bound to a deterministic offline `Model` (no API key
needed) that still flows through the SDK's real `ModelResponse` /
`ResponseOutputMessage` types and `Runner.run()` execution path.

This is a structurally distinct proof point from the LangGraph adapter:
the OpenAI Agents SDK is handoff/turn-based, not a declared node/edge
graph.

## Test

```bash
pytest tests/
```
