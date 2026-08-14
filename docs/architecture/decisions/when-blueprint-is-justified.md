---
description: "ADR: When Blueprint is (and isn't) justified — the real cost of declarative YAML specification versus when hand-written orchestration code is still the right call."
---

# ADR: When Blueprint Is (and Isn't) Justified

**Status:** Accepted.

## Context

`pyagent-blueprint` isn't free — validate/compile/diff/test tooling and a YAML authoring layer are
real overhead versus just writing Python. The question is when that overhead is worth it.

## Decision

**Blueprint is justified when:**

- More than one person needs to review design changes, and a line-level Python diff isn't legible
  enough for that review — Blueprint's semantic diff (`BREAKING`/`WARNING`/`INFO` severity per
  change) is built for exactly this.
- You want to validate a system's structure before spending a token — dangling references and
  schema violations caught statically, not at runtime.
- Governance requirements (budgets, SLAs, memory tiers, HITL checkpoints) need to be declared once
  and either honored or surfaced as a diagnostic — never silently dropped by whichever runtime
  executes it.
- You need to swap which framework executes the system without rewriting the design itself.

**Blueprint is not justified when:**

- It's one person, prototyping, and the design changes every few minutes — the validate/compile
  cycle is overhead until the shape stabilizes.
- The orchestration logic depends on dynamic, runtime-computed control flow that can't be expressed
  as a static graph — Blueprint's IR models agents, typed workflows, and named patterns; that's a
  real constraint, not just a feature gap.
- It's a single agent, single call, with nothing to hand off to — there's no design to declare in
  the first place.

## Consequences

- Adopting Blueprint for a single-developer prototype adds a validate/compile step to every
  iteration with no reviewer to benefit from the diff — pure friction until a second stakeholder is
  actually in the loop.
- Not adopting Blueprint once a system has multiple reviewers means design changes get reviewed as
  prose or as raw Python diffs — the review quality degrades as the system grows, silently.
- The "when not justified" cases aren't permanent — a prototype that stabilizes, or a single-dev
  project that gains a second maintainer, is exactly the point at which the calculus flips.

See [Why Blueprint?](../../why-blueprint.md) for the full case, and the
[Blueprint pillar page](../blueprint.md) for what/when/tradeoffs.
