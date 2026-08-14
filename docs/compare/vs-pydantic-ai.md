---
description: "pyagent-blueprint vs. Pydantic AI — a conceptual comparison of a declarative multi-agent system spec against Pydantic AI's declarative single-agent specs plus code-driven multi-agent orchestration. No pyagent-blueprint adapter exists yet; this page states that plainly."
---

# pyagent-blueprint vs. Pydantic AI

**Status check, up front:** like the [AutoGen](vs-autogen.md) comparison, there is **no
`pyagent-blueprint` Pydantic AI adapter today**. Everything below is a conceptual comparison,
current as of August 2026, based on Pydantic AI's public documentation and GitHub repository — not
a description of working, tested integration code.

## The conceptual difference — what the YAML actually declares

This is the specific point worth being precise about, because both projects now use the phrase
"declarative YAML agent spec" and they don't mean the same scope.

Pydantic AI's **Agent Specs** declare a single agent — model, instructions, model settings, and
capabilities like web search or thinking — loadable from one YAML/JSON file with no Python
construction code. Multi-agent orchestration in Pydantic AI is a separate, code-driven concern:
delegation, programmatic hand-off, or graph-based control flow via `pydantic-graph`, a
type-centric finite-state-machine library. The spec covers one agent; the system that wires several
of them together is still Python.

`pyagent-blueprint`'s manifest declares the **whole system** in the same file: which agents exist,
how they're wired into a named workflow pattern (supervisor, debate, pipeline, ...), which providers
back each one, what contracts and governance apply — the composition itself is the declared artifact,
not just each agent's individual configuration.

Put concretely: if you have three agents and a routing decision between them, Pydantic AI declares
each of the three agents' configs in YAML and expresses the routing in Python; `pyagent-blueprint`
declares the agents *and* the routing pattern *and* the wiring between them all in one YAML file.

## Where this matters less than it sounds

Pydantic AI's approach is a deliberate, defensible design choice, not an oversight — `pydantic-graph`
is a real, typed state-machine library, not "just Python," and for teams already committed to
Pydantic's type-validation ecosystem, staying in Python for orchestration logic while still getting
declarative single-agent configs is a reasonable middle ground. It's also 16,500+ GitHub stars and
one of the fastest-adopted agent frameworks in the Python ecosystem as of this comparison — real,
substantial adoption `pyagent-blueprint` doesn't have.

## What an adapter would need to prove

Per the `RuntimeAdapter` contract, any future `pydantic-ai` adapter has to pass the same
`AdapterConformanceSuite` every existing adapter does. The interesting mapping question is the
inverse of the usual case: instead of mapping PyAgent patterns onto an existing multi-agent execution
engine, an adapter here would need to *generate* the Python delegation/hand-off/graph code Pydantic
AI expects from PyAgent's declared workflow pattern — closer to code generation than to wrapping an
existing orchestration API.

## Where Pydantic AI is the right choice today

If you want type-safe, single-agent configuration with Pydantic's validation guarantees, and are
comfortable keeping multi-agent orchestration logic in Python via `pydantic-graph`, use Pydantic AI
directly. There's currently no `pyagent-blueprint` path onto it. This page will be updated with real,
verified adapter code — following the same standard as the LangGraph and CrewAI pages — if that
mapping work happens.
