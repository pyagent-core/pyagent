---
description: "ADR: Spec-first vs code-first multi-agent architecture — the real tradeoff between declaring a system's design and writing it directly, illustrated against real competitor approaches."
---

# ADR: Spec-First vs. Code-First Architecture

**Status:** Accepted — this is the foundational choice [Why Blueprint?](../../why-blueprint.md)
argues for; this ADR states the tradeoff plainly rather than only the case for one side.

## Context

Every multi-agent framework picks a point on this spectrum. Fully code-first frameworks (AutoGen's
conversable-agent model, hand-written LangGraph graphs) put 100% of the design in Python.
Fully spec-first tools (Pydantic AI's single-agent Agent Specs) declare configuration in YAML/JSON
but leave orchestration in code. `pyagent-blueprint` puts the *whole system* — agents, workflow
pattern, wiring, governance — in the spec.

## Decision

**Choose spec-first (Blueprint) when** the system's design needs to be reviewable, diffable, and
statically validatable independent of the code that executes it — see
[When Blueprint Is (and Isn't) Justified](when-blueprint-is-justified.md).

**Choose code-first when** the orchestration logic is genuinely dynamic (can't be expressed as a
static graph), the team is small enough that Python diffs are sufficient review, or the framework
you need (AutoGen's group chat, a bespoke agent loop) doesn't have a spec-first path today — see
[the AutoGen comparison](../../compare/vs-autogen.md) for a case where no Blueprint adapter exists
yet.

**Note the false binary:** some frameworks split the difference — Pydantic AI declares one agent's
config in YAML while orchestration between agents stays in Python
(see [the Pydantic AI comparison](../../compare/vs-pydantic-ai.md)). That's a legitimate third
point on the spectrum, not a worse version of either extreme — it fits teams that want typed
single-agent config without committing to a spec-first *system* description.

## Consequences

- Spec-first buys diff/review/validate-before-run at the cost of an IR that can only express what
  it was designed to express — dynamic, runtime-computed control flow falls outside it.
- Code-first buys unlimited expressiveness at the cost of every design review being a full code
  review, and no static validation before an LLM is ever called.
- The middle position (spec-first single-agent config, code-first multi-agent wiring) buys
  per-agent type safety without multi-agent-system-level diffability — a real, different tradeoff
  from either extreme, not simply "less spec-first."

See [Why Blueprint?](../../why-blueprint.md) for the full argument and the three comparison pages
above for how this plays out against real frameworks.
