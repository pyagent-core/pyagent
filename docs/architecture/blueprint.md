---
description: "The Blueprint pillar of PyAgent's architecture — declare a multi-agent system as a versioned YAML specification, compiled onto any runtime adapter. What it solves, when to use it, and when not to."
---

# Blueprint

**Verb: Declare.** The Blueprint pillar is `pyagent-blueprint` — a single package, independently
installable, with zero mandatory dependency on the other three pillars.

## What it solves

Hand-written multi-agent orchestration code conflates two different concerns: *design* (which
agents exist, how they're wired, what pattern connects them) and *execution* (the actual Python
that runs it). That conflation means every design review is a full code review, every diff is a
line-level Python diff instead of a semantic one, and there's no way to statically validate a
system's shape before spending a token on it.

Blueprint separates the two. The design becomes a typed YAML document — validated, diffable,
testable against a `MockLLM` with no live API calls, and compiled onto whichever `RuntimeAdapter`
actually executes it.

## When to use

- More than one person needs to review changes to the system's design, and a Python diff isn't
  legible enough for that review.
- You want to validate a system's structure (dangling references, schema violations) before an LLM
  is ever called.
- You need to swap which framework executes the system (LangGraph, CrewAI, the native `pyagent`
  registry, ...) without rewriting the design.
- Governance requirements (budgets, SLAs, memory tiers, human-in-the-loop checkpoints) need to be
  declared once and either honored or surfaced as a diagnostic — never silently dropped.

## When not to use

- Your orchestration logic depends on dynamic, runtime-computed control flow that can't be
  expressed as a static graph (e.g. an agent that decides to spin up an arbitrary number of
  sub-agents from a live computation) — hand-written code in your chosen framework is still the
  right tool.
- It's a single agent, single call, with no second agent to wire in — there's no design to declare.
  See [why-blueprint.md](../why-blueprint.md#when-you-dont-need-pyagent-at-all).
- You're prototyping and the design changes every few minutes — the validate/compile cycle is
  overhead until the shape stabilizes.

## Tradeoffs

Declarative-by-design is a real constraint, not just a feature: anything Blueprint's IR can't
express (agents, typed workflows, named patterns), you can't declare — you drop to Python via a
custom `RuntimeAdapter` instead. That's the tradeoff for getting diff/review/validate for free on
everything the IR *can* express.

## Package

`pip install pyagent-blueprint` — zero mandatory runtime dependency beyond `pydantic`, `pyyaml`,
and `click`. Runtime execution requires installing an adapter (bundled zero-dependency reference
adapters, or an extra like `pyagent-blueprint[langgraph]`).

## Example

```yaml
api_version: pyagent/v1
metadata:
  name: customer-support
agents:
  classifier: { prompt: "Classify into: billing, tech, general" }
  billing: { prompt: "Handle billing inquiries" }
workflows:
  support:
    pattern: supervisor
    agents: { classifier: classifier, routes: { billing: billing } }
```

```bash
pyagent-blueprint validate customer-support.yaml
pyagent-blueprint test customer-support.yaml
```

See the full [Blueprint guide](../guides/blueprint.md) and [Why Blueprint?](../why-blueprint.md) for
the complete spec format, CLI, and cross-framework comparison.

## Related pillars

Blueprint's `agents`/`workflows` compile onto [Execution & Routing](execution.md); its `providers`
block feeds routing; its `context`/`observability` blocks wire [Context & Memory](context.md) and
[Observability](observability.md) — but none of that wiring is required to use Blueprint's
validate/diff/test capabilities on their own.
