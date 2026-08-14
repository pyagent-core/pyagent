---
description: "ADR: Working vs Session vs Semantic memory in pyagent-context — matching a memory tier to how long state actually needs to survive."
---

# ADR: Working vs. Session vs. Semantic Memory

**Status:** Accepted.

## Context

`pyagent-context` ships three memory tiers. Using the wrong one is a common source of either lost
state (using a tier that doesn't survive long enough) or unnecessary complexity (using a
longer-lived tier than the data needs).

## Decision

Match the tier to how long the state actually needs to survive — nothing more:

- **`WorkingMemory`** — state only needs to survive within a single agent turn. Cheapest and
  fastest tier; nothing persists once the turn ends. Don't reach further unless you actually need
  state to outlive the turn.
- **`SessionMemory`** — multiple agents in one run need to share state across turns. Scoped to one
  run; nothing carries over to the next session automatically.
- **`SemanticMemoryProtocol`** — knowledge needs to persist and be retrieved across separate
  runs/sessions. The built-in `InMemorySemanticStore` doesn't survive a process restart — a durable
  backend is a protocol implementation you provide.

## Consequences

- Defaulting to `SemanticMemoryProtocol` "to be safe" when `WorkingMemory` would do adds a
  dependency and a persistence concern (what backend? what TTL?) for data that never needed to
  outlive one turn.
- Defaulting to `WorkingMemory` for state that actually needs to survive across a run silently
  loses that state the moment the turn ends — a correctness bug, not a performance one.
- `SessionMemory` gives no durability guarantee beyond the run — if "remember this next week" is a
  real requirement, `SessionMemory` alone won't satisfy it; you need `SemanticMemoryProtocol` with a
  real backend.
- If no state needs to persist across agents or turns at all, none of the three tiers is needed —
  see [why-blueprint.md's "when you don't need PyAgent at all"](../../why-blueprint.md#when-you-dont-need-pyagent-at-all).

See the [Context & Memory pillar page](../index.md#context-memory) and the [Context guide](../../guides/context.md)
for the full API.
