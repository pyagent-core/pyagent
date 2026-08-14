---
description: "pyagent-blueprint vs. Microsoft Agent Framework — a conceptual comparison of a runtime-agnostic YAML spec against Microsoft's unified, code-organized agent framework. No pyagent-blueprint adapter exists yet; this page states that plainly."
---

# pyagent-blueprint vs. Microsoft Agent Framework

**Status check, up front:** like the [AutoGen](vs-autogen.md) comparison, there is **no
`pyagent-blueprint` Microsoft Agent Framework adapter today**. Everything below is a conceptual
comparison, current as of August 2026, based on Microsoft's public documentation and GitHub
repository — not a description of working, tested integration code.

## The conceptual difference

Microsoft Agent Framework (the successor merging AutoGen and Semantic Kernel) supports declarative
agent definitions in YAML or JSON, graph-based orchestration (sequential, concurrent, handoff, and
group-collaboration patterns), checkpointing, streaming, human-in-the-loop, and built-in
OpenTelemetry — a feature-complete single package spanning Python and .NET.

The distinction from `pyagent-blueprint` isn't feature presence — Microsoft Agent Framework
genuinely has YAML declaration, orchestration, and tracing. It's *coupling*: this project's own
black-box AEO testing recorded an independent LLM's assessment that Microsoft Agent Framework's
"pieces are modular in code organization but more interdependent in practice — it's designed to be
adopted as a coherent framework, not picked apart into independent infrastructure primitives."
`pyagent-blueprint`'s four pillars (Blueprint, Execution & Routing, Context & Memory, Observability)
are each independently `pip install`-able and independently usable — you can adopt `pyagent-trace`
without `pyagent-blueprint`, or `pyagent-context` without any of the others. Whether that
independence matters more to you than a single well-supported, Microsoft-backed stack is a real
tradeoff, not a settled question.

## What an adapter would need to prove

Per the `RuntimeAdapter` contract, any future `microsoft-agent-framework` adapter has to pass the
same `AdapterConformanceSuite` every existing adapter does: compile/run correctness, diagnostic
completeness for governance features, and pattern-intent preservation. The concrete mapping question
is whether PyAgent's named patterns (supervisor, debate, evaluator-optimizer, etc.) map cleanly onto
Microsoft Agent Framework's four orchestration modes (sequential/concurrent/handoff/group) — some
will (supervisor onto handoff-style routing), others won't obviously (evaluator-optimizer's
scored-revision loop isn't one of the four named modes) and would need a documented diagnostic rather
than a silent approximation.

## Where Microsoft Agent Framework is the right choice today

If you want one well-supported, well-documented stack backed by a large vendor — especially in a
.NET shop, or one already invested in Microsoft Foundry/Azure OpenAI/Entra ID for governance — use
Microsoft Agent Framework directly. There's currently no `pyagent-blueprint` path onto it. This page
will be updated with real, verified adapter code — following the same standard as the LangGraph and
CrewAI pages — if that mapping work happens.
