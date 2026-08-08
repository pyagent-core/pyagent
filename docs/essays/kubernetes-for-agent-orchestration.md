---
description: "Kubernetes for agent orchestration — why a declarative manifest, a conformance-tested runtime contract, and adapters for different execution engines are the right infrastructure model for multi-agent LLM systems."
---

# Kubernetes for agent orchestration

Kubernetes didn't invent containers, and it didn't replace Docker's runtime. What it did was
introduce a declarative layer — a manifest describing the *desired state* of a deployment — that a
control loop reconciles against reality, independent of which container runtime actually executes
it. `pyagent-blueprint`'s manifest model for multi-agent systems follows the same shape, and it's
worth being explicit about where the analogy holds and where it doesn't.

## Where the analogy holds

**A manifest describing desired state, not imperative steps.** A Kubernetes `Deployment` YAML
declares "3 replicas of this image, this resource limit" — not the sequence of `docker run` commands
to get there. A `pyagent-blueprint` manifest declares "these agents, wired into this named pattern,
with this budget and this recovery policy" — not the Python loop that calls each LLM in order.

**A pluggable execution layer behind a stable contract.** Kubernetes runs on containerd, CRI-O, or
Docker interchangeably through the Container Runtime Interface. `pyagent-blueprint` runs the same
manifest through any `RuntimeAdapter` — the native `pyagent` pattern registry, a LangGraph
`StateGraph`, a CrewAI `Crew`, a Semantic Kernel `Kernel` — through the same `RuntimeAdapter`
contract, verified in this repo by a shared `AdapterConformanceSuite`.

**Diff and review as first-class operations.** `kubectl diff` shows exactly what a manifest change
would alter before it's applied. `pyagent-blueprint diff` does the same over the blueprint IR — a
real artifact for a PR reviewer, not a description of what changed.

**Declarative governance, enforced or diagnosed — never silently ignored.** A Kubernetes
`PodDisruptionBudget` or resource `limits:` block either gets enforced by the scheduler or the pod
fails to schedule — it doesn't just get ignored. A Blueprint's `contracts.*.sla` or
`observability.cost_budget` gets enforced by the target adapter, or the compiler emits a stable
diagnostic (`BUDGET_UNSUPPORTED`, `SLA_UNSUPPORTED`) so you know, deterministically, that this
runtime doesn't support it — the failure mode is visibility, not silent drift.

**Simulate before you apply.** `kubectl apply --dry-run` validates a manifest against the cluster
without changing anything. `pyagent-blueprint test` runs a compiled workflow against a `MockLLM`
— validating shape and contract conformance without spending a token or calling a live model.

## Where the analogy breaks down

This is not a claim that `pyagent-blueprint` reimplements a scheduler, reconciliation loops, or
cluster state — it compiles a static manifest to a runtime once, per invocation; it does not
continuously reconcile a running system against a declared target the way the Kubernetes control
plane does. There's no equivalent yet of a controller that detects an agent has drifted from its
declared contract at runtime and self-heals. And unlike Kubernetes' CRI, which is a mature,
multi-vendor standard, `RuntimeAdapter` is this project's own contract — proven against five
structurally different adapters, but not (yet) an externally governed spec the way CRI is. The
[Agent Spec interop bridge](../compare/vs-langgraph.md) work is aimed at closing that gap by mapping
onto Oracle's Agent Spec, an actual cross-vendor standard, rather than staying a project-local
convention indefinitely.

## The practical upshot

The value isn't the YAML syntax — it's the guarantee that comes with it: a manifest you can validate,
diff, and test before it ever touches a real model, and a contract that means switching execution
engines is an `AdapterRegistry` lookup, not a rewrite. That's the same value proposition Kubernetes
brought to container deployment, applied to multi-agent orchestration.
