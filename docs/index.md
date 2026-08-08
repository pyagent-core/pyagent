---
template: home.html
description: "PyAgent is a production stack for multi-agent LLM systems — declare agents in YAML, orchestrate with 18 named patterns, share three-tier memory, and trace every call and cost."
---

<!--
The rendered home page is the bespoke template at docs/overrides/home.html
(declared via `template:` above), which owns the hero, the four pillar cards,
the "Why PyAgent?" comparison, and the quick start. This Markdown body is a lean
routing fallback: it links to the four pillars and the quickstart, and points at
the dedicated pattern catalog rather than re-listing all 18 patterns here (that
lives on packages/patterns/index.md) or duplicating the comparison table.
-->

# PyAgent

**A production stack for multi-agent LLM systems** — declare, execute, remember, and observe.

[Get Started](getting-started.md){ .md-button .md-button--primary }
&nbsp;
[Browse the pattern library](packages/patterns/index.md){ .md-button }

## The four pillars

1. **[Manifest](packages/blueprint/index.md)** — declare your entire agent system in a single
   typed YAML file with `pyagent-blueprint`; validate, compile, diff, and test from the spec.
2. **[Execution & Routing](packages/patterns/index.md)** — 18 named orchestration patterns run real
   agents against real providers, with difficulty-based model routing and inter-agent compression.
3. **[Context & Memory](packages/context.md)** — three-tier memory shared across a run, with trust
   levels and PII redaction built in.
4. **[Observability](packages/trace.md)** — every call traced and every cost tracked, with a
   [Studio dashboard](guides/studio.md) for traces, costs, governance, and provider health.

## Start here

- **New to multi-agent systems?** [Getting Started](getting-started.md) → [Blueprint guide](guides/blueprint.md) → [Composition guide](guides/composition.md)
- **Adding to an existing codebase?** [Providers](guides/providers.md) · [Router](guides/router.md) · [Context](guides/context.md)
- **Building for production?** [Tracing](guides/tracing.md) · [Studio](guides/studio.md) · [Recovery](guides/recovery.md)

## Explore

- [Design Patterns](packages/patterns/index.md) — the full 18-pattern catalog with a comparison-and-selection guide
- [Cookbook](cookbook/index.md) — complete, runnable multi-agent recipes by domain
- [Benchmarks](benchmarks.md) — cost, quality, latency, and routing-savings measurements
