---
description: "pyagent-blueprint vs. AutoGen — a conceptual comparison of declarative YAML manifests against AutoGen's conversable-agent model. No pyagent-blueprint AutoGen adapter exists yet; this page states that plainly."
---

# pyagent-blueprint vs. AutoGen

**Status check, up front:** unlike the [LangGraph](vs-langgraph.md) and [CrewAI](vs-crewai.md)
comparisons, there is **no `pyagent-blueprint` AutoGen adapter yet**. AutoGen was explicitly
deprioritized to last in the adapter rollout (after LangGraph, OpenAI Agents SDK, CrewAI, and
Semantic Kernel) and hasn't shipped. Everything below is a conceptual comparison of the two
models, not a description of working, tested integration code — we're not going to claim
portability that doesn't exist yet.

## The conceptual difference

AutoGen models multi-agent systems as **conversable agents** exchanging messages in a group chat —
agents are defined with a `system_message` and register reply functions or tools, and a
`GroupChatManager` (or two-agent `initiate_chat`) drives the conversation loop. It's a
message-passing model rather than a fixed graph or role/task list.

`pyagent-blueprint`'s IR models a workflow as a named pattern (pipeline, supervisor, debate, etc.)
wiring specific agents into that pattern's slots — closer to AutoGen's structured patterns (like its
own two-agent chat or nested chats) than to fully open-ended group chat, since the manifest declares
the shape of the conversation ahead of time rather than letting agents dynamically decide who speaks
next.

## What an AutoGen adapter would need to prove

Per the `RuntimeAdapter` contract, any future `autogen` adapter has to pass the same
`AdapterConformanceSuite` every existing adapter does: compile/run correctness, diagnostic
completeness for governance features, and pattern-intent preservation. Concretely, that means
mapping named patterns onto AutoGen constructs — e.g. `pipeline`/`sequential` patterns onto chained
`initiate_chat` calls, `supervisor`/`debate` patterns onto a `GroupChatManager` with a fixed
speaker-selection method — and reporting a stable diagnostic (not a silent drop) wherever AutoGen has
no equivalent for a declared governance feature like a budget or memory tier.

## Where AutoGen is the right choice today

If you need AutoGen specifically — its group-chat conversation model, or its ecosystem of AutoGen
Studio / AutoGen-specific tooling — write directly against the AutoGen SDK. There's currently no
`pyagent-blueprint` path onto it. This page will be updated (with real, verified code, following the
same standard set by the LangGraph and CrewAI pages) once an adapter actually ships.
