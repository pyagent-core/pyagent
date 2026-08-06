# pyagent-blueprint-adapter-semantic-kernel

A [pyagent-blueprint](https://pyagent.org) `RuntimeAdapter` targeting
**Microsoft Semantic Kernel**.

Published separately from `pyagent-blueprint` core so Semantic Kernel's
release cadence never destabilizes core CI. Self-certifies against the
shared `AdapterConformanceSuite`.

## Install

```bash
pip install -e .[test]
```

## Model

Each blueprint workflow compiles to a chain of Semantic Kernel
`ChatCompletionAgent`s (one per referenced agent, ref order), executed in
sequence — each agent's response text becomes the next agent's input
message. Each agent's `ChatCompletionClientBase` service is a
deterministic offline implementation (no API key needed) that still
flows through the SDK's real `ChatMessageContent` type and
`ChatCompletionAgent.get_response()` execution path.

This is the fourth structurally distinct proof point (after LangGraph's
declared graph, the OpenAI Agents SDK's handoff/turn model, and CrewAI's
role-based model): Semantic Kernel is event/service-oriented — a
`Kernel` hosts pluggable AI services that agents bind to.

## Test

```bash
pytest tests/
```
