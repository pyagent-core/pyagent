---
description: "Configure context and memory in a PyAgent blueprint — wire the ContextLedger into your agents."
---

# Blueprint — Context Config

The `context:` block configures per-run memory, compression, and PII redaction. When present, the compiler wires a `ContextLedger` automatically — no extra Python code needed.

---

## ContextConfigSpec Fields

```yaml
context:
  memory:
    working_max_tokens: 20000    # Working memory cap (in-process)
    session_backend: sqlite      # Persistence across turns: 'json' | 'sqlite'
    semantic_enabled: true       # Enable vector search (requires chromadb)
  compression:
    policy: semantic_lossless    # none | fifo | semantic_lossless | sawtooth
    target_ratio: 0.6            # Compress to 60% of current token count
    threshold_tokens: 15000      # Trigger compression above this threshold
    floor_tokens: 5000           # Never compress below this floor
  redaction:
    max_sensitivity: internal    # public | internal | confidential | restricted
    exclude_above: false         # If true, strip items above max_sensitivity
```

---

## Memory Tiers

### Working Memory

In-process, bounded by `working_max_tokens`. Holds the current conversation turn. Automatically evicted as the conversation grows past the cap.

```yaml
context:
  memory:
    working_max_tokens: 20000
```

Corresponds to `WorkingMemory(max_tokens=20000)` in `pyagent-context`.

### Session Memory

Persists across turns to a file or SQLite database — useful for multi-turn conversations and stateful agents.

```yaml
context:
  memory:
    session_backend: sqlite   # stored in .pyagent/session.db
```

Use `json` for a human-readable file. Use `sqlite` for better concurrency and query performance.

### Semantic Memory

Vector-indexed storage for similarity search — agents can retrieve the most relevant past context rather than loading all history.

```yaml
context:
  memory:
    semantic_enabled: true    # Requires: pip install pyagent-context[chromadb]
```

---

## Compression Policies

Compression triggers when the total context token count exceeds `threshold_tokens`, then reduces it toward `target_ratio × current_tokens`, with `floor_tokens` as a hard minimum.

| Policy | Behavior |
|--------|-----------|
| `none` | No compression — context grows unbounded |
| `fifo` | Drop oldest items first |
| `semantic_lossless` | Keep high-trust and recent items; drop redundant low-trust ones |
| `sawtooth` | Aggressive drop then gradual rebuild — good for long-running agents |

```yaml
context:
  compression:
    policy: semantic_lossless
    target_ratio: 0.6
    threshold_tokens: 15000
    floor_tokens: 5000
```

For most production uses, `semantic_lossless` is the right default — it preserves verified facts (from databases, tool calls) and drops redundant conversation noise.

---

## Redaction

Strip items above a sensitivity level before injecting context into LLM calls. Prevents PII from leaking into prompts unintentionally.

```yaml
context:
  redaction:
    max_sensitivity: internal    # public, internal, confidential, restricted
    exclude_above: false
```

Items tagged `Sensitivity.PII` or `Sensitivity.CONFIDENTIAL` in the `ContextLedger` will be excluded from the context injected into agent prompts.

Sensitivity levels (ascending):

| Level | Description |
|-------|-------------|
| `public` | Safe to expose anywhere |
| `internal` | Internal systems only |
| `confidential` | Restricted to specific roles |
| `restricted` | Most sensitive — PII, credentials, etc. |

---

## Wiring Context to Agents at Runtime

When the blueprint has a `context:` block, the compiler calls `graph.wire_context(ledger)` — this sets the same ledger on every agent in the graph:

```python
from pyagent_blueprint import load_blueprint, BlueprintCompiler
from pyagent_context import ContextLedger, ContextItem, TrustLevel

spec  = load_blueprint("blueprint.yaml")
graph = BlueprintCompiler().compile(spec)

# Optional: pre-populate with verified facts
ledger = ContextLedger()
ledger.append(ContextItem(
    content="Customer ID: C-10482, account since 2022",
    source="database",
    trust=TrustLevel.VERIFIED,
))
graph.wire_context(ledger)

result = asyncio.run(graph.run("main", "What are my account details?"))
```

---

## Example: Full Context Config

```yaml
context:
  memory:
    working_max_tokens: 20000
    session_backend: sqlite
    semantic_enabled: true
  compression:
    policy: semantic_lossless
    target_ratio: 0.6
    threshold_tokens: 15000
    floor_tokens: 5000
  redaction:
    max_sensitivity: internal
    exclude_above: false
```

---

## See Also

- [Context Package](../context.md) — `ContextLedger`, `WorkingMemory`, `SessionMemory`, `SemanticMemory`
- [Context Guide](../../guides/context.md) — narrative walkthrough
- [Full Spec Reference](spec-format.md)
