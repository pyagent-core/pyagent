---
description: "The Context & Memory pillar of PyAgent's architecture — three-tier memory with a trust-aware context ledger and PII redaction. What it solves, when to use it, and when not to."
---

# Context & Memory

**Verb: Remember.** The Context & Memory pillar is `pyagent-context` — one package, independently
installable.

## What it solves

Multi-agent state has three different lifetimes that get conflated when handled ad hoc: state that
only needs to survive one turn, state shared across a run, and state that needs to persist across
separate sessions. On top of that, not every agent should automatically see everything — an
external-tool-facing agent shouldn't get the same context an internal-only agent does, and PII
needs redaction before it crosses that boundary.

## When to use

- Multiple agents in a run need to share state across turns.
- Some agents (e.g. external-facing) shouldn't automatically receive everything internal agents see
  — trust levels need enforcing, not just convention.
- Context may contain PII that needs redaction before reaching a downstream agent or tool.
- Long sessions are approaching a token budget and need compression, not just truncation.
- You need an audit trail of which agent produced or saw which piece of context.

## When not to use

- **Persistent memory is unnecessary** for a single agent, single call, with nothing to persist
  across turns or runs — there's no cross-agent context to manage, and reaching for a memory tier
  here adds a dependency for zero benefit.
- Every agent in the system is equally trusted with all context — `TrustLevel`/`TrustAwareRetriever`
  add design work (classifying every item) for no enforcement benefit.
- Context is entirely non-sensitive synthetic data — `ContextRedactor`/`Sensitivity` classification
  is pure overhead.

## Tradeoffs

`WorkingMemory` is cheapest but nothing survives the turn. `SessionMemory` is scoped to one run —
nothing carries to the next session automatically. `SemanticMemoryProtocol`'s built-in
`InMemorySemanticStore` doesn't persist across process restarts — a durable backend is a protocol
implementation you provide. Redaction and compression are both lossy by design; over-aggressive
rules can strip context an agent legitimately needed.

## Package

`pip install pyagent-context` — `WorkingMemory`, `SessionMemory`, `SemanticMemoryProtocol`,
`ContextLedger`, `TrustLevel`, `Sensitivity`, `ContextRedactor`, `TrustAwareRetriever`,
`CompressionPolicy`, `ContextCompressor`.

## Example

```python
from pyagent_context import ContextLedger, TrustLevel

ledger = ContextLedger()
ledger.add(item, trust_level=TrustLevel.INTERNAL)
visible = ledger.retrieve_for(agent="external_tool_agent")  # trust-filtered
```

See the [Context guide](../guides/context.md) for the complete three-tier memory model, trust
levels, and redaction API.

## Related pillars

Context is often shared by agents wired together via [Execution & Routing](execution.md), and can
be declared inside a [Blueprint](blueprint.md)'s `context:` block. Context-tier changes and
redaction events are traceable via [Observability](observability.md) — none of that is required to
use the memory tiers standalone.
