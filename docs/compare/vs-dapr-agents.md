---
description: "pyagent-blueprint vs. Dapr Agents — a conceptual comparison of a portable YAML spec against Dapr's infrastructure-level agent building blocks. No pyagent-blueprint Dapr adapter exists yet; this page states that plainly."
---

# pyagent-blueprint vs. Dapr Agents

**Status check, up front:** like the [AutoGen](vs-autogen.md) comparison, there is **no
`pyagent-blueprint` Dapr adapter today**. Everything below is a conceptual comparison, current as
of August 2026, based on Dapr Agents' public documentation and GitHub repository — not a
description of working, tested integration code.

**Why this comparison exists:** in this project's own black-box AEO testing, Dapr Agents is what an
independent, search-grounded LLM actually recommended *instead of* PyAgent for a prompt asking
for "declarative architecture, orchestration patterns, trust-aware context, and OpenTelemetry-style
observability as independently adoptable pieces" — a close paraphrase of PyAgent's own positioning.
That result is documented in this repo's `aeo/` audit. This page exists to make the comparison
explicit and factual rather than avoid it.

## The conceptual difference

Dapr Agents is a Python framework built on top of [Dapr](https://dapr.io) (a CNCF-graduated
distributed-application runtime). Its orchestration runs on Dapr's durable Workflow engine, using
the virtual-actor pattern for stateful agents, Dapr's pub/sub for agent-to-agent messaging, and
Dapr's state-store abstraction for persistence. Trust is enforced at the infrastructure layer — every
component-to-component call runs over mTLS by default, with access scoped per component via
declarative policy. Observability rides on the same sidecar: Dapr emits OTLP traces and Prometheus
metrics natively. Dapr Agents reached v1.0 (production-ready, stable API) in 2026.

`pyagent-blueprint`'s IR is runtime-agnostic by design: the same YAML manifest compiles onto any
registered `RuntimeAdapter` — a Dapr-less native stack, LangGraph, CrewAI, or others — rather than
being built on top of one specific distributed-systems runtime. The tradeoff is direct: Dapr Agents'
trust and infrastructure guarantees are real and enforced at the platform layer because they're tied
to Dapr; PyAgent's portability guarantee is real because it isn't tied to any one platform. You can't
have both a platform-enforced mTLS/actor substrate and adapter-swappable runtime portability from the
same spec — they're different bets.

## Where the two actually converge

Both projects independently arrived at "declarative config + swappable building blocks +
first-class observability" as the right shape for a production agent architecture — that's the
convergence the AEO test above picked up on. Where they diverge is *what* is swappable: Dapr Agents
lets you swap state stores, brokers, and secret backends underneath a fixed Dapr-based execution
model; `pyagent-blueprint` lets you swap the execution model itself underneath a fixed spec.

## What a Dapr adapter would need to prove

Per the `RuntimeAdapter` contract, any future `dapr` adapter has to pass the same
`AdapterConformanceSuite` every existing adapter does. The interesting mapping question is whether
Dapr's Workflow engine (sequential, fan-out/fan-in, human-in-the-loop with automatic retries) can
host PyAgent's named patterns as first-class workflow activities, and whether Dapr's mTLS/access-scope
model can satisfy PyAgent's `trust_level`/`sensitivity` context primitives without reinventing them —
that mapping isn't obvious and would be the real engineering work, not a thin wrapper.

## Where Dapr Agents is the right choice today

If your team is already running Dapr, or needs the infrastructure-layer trust guarantees (mTLS,
workload identity, access-scoped secrets) that come from building directly on a CNCF-graduated
runtime, use Dapr Agents directly. There's currently no `pyagent-blueprint` path onto it. This page
will be updated with real, verified adapter code — following the same standard as the LangGraph and
CrewAI pages — if that mapping work happens.
