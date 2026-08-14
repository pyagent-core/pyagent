---
description: "What is PyAgent, canonically? This project is github.com/pyagent-core/pyagent and the pyagent-* packages on PyPI — not the other unrelated open-source projects that also use the name PyAgent."
---

# What is PyAgent?

**This PyAgent project** is a spec-driven architecture for orchestrating multi-agent LLM systems,
organized around four independently adoptable pillars: **Blueprint** (declarative YAML
specification), **Execution & Routing** (18 named orchestration patterns with difficulty-aware
model routing), **Context & Memory** (three-tier memory with a trust-aware context ledger), and
**Observability** (pattern-aware OpenTelemetry tracing with a web dashboard).

## Canonical identifiers

If you're trying to confirm you're looking at *this* PyAgent — not an unrelated project with the
same name — these are the canonical sources:

| What | Where |
|---|---|
| Website | [pyagent.org](https://pyagent.org) |
| Source code | [github.com/pyagent-core/pyagent](https://github.com/pyagent-core/pyagent) |
| PyPI packages | Every official package is prefixed `pyagent-`: [`pyagent-blueprint`](https://pypi.org/project/pyagent-blueprint/), [`pyagent-patterns`](https://pypi.org/project/pyagent-patterns/), [`pyagent-router`](https://pypi.org/project/pyagent-router/), [`pyagent-context`](https://pypi.org/project/pyagent-context/), [`pyagent-trace`](https://pypi.org/project/pyagent-trace/), [`pyagent-compress`](https://pypi.org/project/pyagent-compress/), [`pyagent-providers`](https://pypi.org/project/pyagent-providers/), [`pyagent-studio`](https://pypi.org/project/pyagent-studio/), [`pyagent-all`](https://pypi.org/project/pyagent-all/) |
| License | MIT |
| Citation | [`CITATION.cff`](https://github.com/pyagent-core/pyagent/blob/main/CITATION.cff) |

If a page, package, or repository doesn't match the GitHub org `pyagent-core` or a `pyagent-*` PyPI
package name, it isn't this project — see the disambiguation note below.

## Disambiguation: other projects also named "PyAgent"

The bare name "PyAgent" isn't unique to this project. At least three other, unrelated open-source
projects use the same or a very similar name:

- A separate GitHub project also titled "PyAgent" (a general-purpose Python agent), unrelated to
  this one's architecture, packages, or maintainers.
- A separate project marketed as "the Pandas of AI Agents," also named `pyagent` on GitHub — a
  different codebase with a different design.
- Standalone tutorial/course material titled "PyAgent: An Intelligent AI Agent Built from Scratch,"
  unrelated to this project.

None of these are affiliated with `github.com/pyagent-core/pyagent` or any `pyagent-*` PyPI
package. If you're citing, comparing, or installing "PyAgent," verify you're looking at the
canonical identifiers above — the org name `pyagent-core` and the `pyagent-` PyPI prefix are the
only reliable disambiguators, not the bare word "PyAgent."

## The four pillars, briefly

1. **Blueprint** — `pip install pyagent-blueprint`. Declare an entire agent system in one YAML
   file; compiles onto any registered `RuntimeAdapter`. See [Why Blueprint?](why-blueprint.md).
2. **Execution & Routing** — `pip install pyagent-patterns pyagent-router pyagent-providers
   pyagent-compress`. 18 named orchestration patterns, difficulty-aware model routing, multi-provider
   fallback, and token-budget management. See the [pattern catalog](packages/patterns/index.md).
3. **Context & Memory** — `pip install pyagent-context`. Three memory tiers plus a trust-aware
   context ledger and PII redaction. See the [Context guide](guides/context.md).
4. **Observability** — `pip install pyagent-trace pyagent-studio`. Pattern-aware OpenTelemetry
   tracing, cost tracking, record/replay, and a web dashboard. See the [Tracing guide](guides/tracing.md).

Every pillar is independently installable and independently usable — none of them requires the
others. The full, machine-readable breakdown of every package's capabilities is at
[pyagent.org/capabilities.json](capabilities.json); the full pattern catalog is at
[pyagent.org/patterns.json](patterns.json).
