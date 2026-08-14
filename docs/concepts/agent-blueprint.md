---
description: "What is an agent blueprint? Spec-driven development for multi-agent systems — a declarative YAML manifest that defines an entire agent system: agents, workflows, providers, contracts, and governance, compiled onto any runtime adapter."
---

# What is an agent blueprint?

An **agent blueprint** is a declarative document — YAML or JSON — that fully describes a multi-agent
system: which agents exist, how they're wired into named orchestration patterns, which LLM providers
back them, what contracts (input/output shape, SLAs) they must satisfy, and what governance
(budgets, memory tiers, guardrails, recovery, human-in-the-loop checkpoints) applies. It's a
manifest, not a script — the system's shape is data, not control flow buried in Python.

This is **spec-driven development** applied to multi-agent systems: the same discipline that made
Terraform and Kubernetes manifests the default way to describe infrastructure, applied to *which
agents exist and how they're wired together*. The spec is the source of truth; the runtime is an
interchangeable detail the spec doesn't hard-code.

## The anatomy of a blueprint

```yaml
api_version: pyagent/v1
metadata:
  name: customer-support
  version: 1.0.0
  owner: platform-team

providers:                 # LLM bindings — model, tokens, timeout
  primary:
    model: gpt-4.1-mini
  fallback:
    model: gpt-4.1-nano

agents:                    # Agent definitions — prompt, provider, guardrails
  classifier:
    prompt: "Classify into: billing, tech, general"
    provider: primary
  billing:
    prompt: "Handle billing inquiries"
    provider: primary
    guardrails: [pii_redact]

workflows:                  # Named-pattern wiring + recovery policy
  support:
    pattern: supervisor
    agents:
      classifier: classifier
      routes: {billing: billing}
    recovery:
      max_retries: 2
      fallback_provider: fallback

contracts:                  # Input/output schema + SLA
  support:
    input: {type: string, max_tokens: 2000}
    output: {type: string}
    sla: {latency_p95_ms: 5000, cost_max_usd: 0.05}

observability:              # Tracing + cost budgets
  tracing: {enabled: true}
  cost_budget: {daily_usd: 100.0}
```

Every top-level block maps onto a real, compilable capability, not just documentation: `providers`
feeds `pyagent-router`'s routing; `agents`/`workflows` compile to a `RuntimeAdapter`'s
`CompiledArtifact`; `contracts` become validated I/O + SLA checks; `observability` wires
`pyagent-trace`.

## Why a manifest instead of code

A hand-written orchestration script conflates *design* (which agents, wired how) with
*implementation* (which SDK, which execution loop). A blueprint separates them:

- **Version and diff it like infrastructure.** `pyagent-blueprint diff v1.yaml v2.yaml` shows exactly
  which agent, route, or SLA changed — a real code review artifact, not a prose changelog.
- **Validate before running anything.** Static analysis catches dangling agent references or schema
  violations before an LLM call happens.
- **Compile it onto any registered runtime.** The same manifest runs on the bundled `pyagent`
  pattern registry, a zero-dependency stdlib adapter, or a third-party adapter for LangGraph, CrewAI,
  Semantic Kernel, or the OpenAI Agents SDK — see [Why Blueprint?](../why-blueprint.md) for the full
  proof.
- **Test without spending tokens.** `pyagent-blueprint test` runs contract conformance checks against
  a `MockLLM`, so CI can validate a system's shape and contract conformance for free.
- **Never silently drop governance.** Every declared budget, memory tier, guardrail, recovery policy,
  or HITL checkpoint is either honored by the target adapter or surfaced as a stable diagnostic code
  (e.g. `BUDGET_UNSUPPORTED`) — you always know what a runtime actually supports.

## Where a blueprint fits in the stack

A blueprint is Pillar 1 of PyAgent's four-pillar spec-driven architecture — Blueprint, Execution & Routing,
Context & Memory, and Observability. See the [Blueprint guide](../guides/blueprint.md) for the full
spec format, or [What is multi-agent orchestration?](multi-agent-orchestration.md) for the
coordination patterns a blueprint's `workflows:` block declares.
