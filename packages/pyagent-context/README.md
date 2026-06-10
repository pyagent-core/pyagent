# pyagent-context

**Three-tier memory with trust-aware context ledger** for multi-agent LLM systems. Structured context management with trust levels, sensitivity classification, compression policies, and lifecycle management.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](../../LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

## Install

```bash
pip install pyagent-context                   # Core (working + session + semantic memory)
pip install pyagent-context[compress]         # + ContextCompressor with pyagent-compress
pip install pyagent-context[chromadb]         # + ChromaDB semantic memory backend
```

Depends on: `pyagent-patterns`.

## Why Structured Context?

Without `pyagent-context`, multi-agent workflows pass a flat `list[Message]` that grows unbounded. You lose track of *who* said *what*, *when*, and *how much to trust it*. This package adds trust levels, sensitivity tiers, expiry, compression, and three memory tiers — so your agents always work with the right context.

## ContextItem — Everything Has Metadata

```python
import time
from pyagent_context import ContextItem, TrustLevel, Sensitivity

item = ContextItem(
    content="Revenue grew 15% YoY to $25.2B",
    source="analyst",
    trust_level=TrustLevel.VERIFIED,       # verified | inferred | user | external
    sensitivity=Sensitivity.INTERNAL,       # public | internal | confidential | restricted
    expires_at=time.time() + 3600,         # auto-expire in 1 hour
    derived_from="abc123",                  # parent item ID
)

print(item.id)               # unique 12-char hex
print(item.token_estimate)   # auto-calculated: len(content) // 4
print(item.is_expired)       # False (still within TTL)
print(item.age_seconds)      # seconds since creation

# Serialize / deserialize
data = item.to_dict()
restored = ContextItem.from_dict(data)
```

## ContextLedger — Append-Only Context Log

```python
from pyagent_context import ContextLedger, TrustLevel

ledger = ContextLedger()

# Add items
ledger.add("User asked about Q3 earnings", "user", TrustLevel.USER_PROVIDED)
ledger.add("Revenue: $25.2B (+8% YoY)", "analyst", TrustLevel.VERIFIED)
ledger.add("I think margins will improve", "forecaster", TrustLevel.INFERRED)

# Query by trust
verified = ledger.query(min_trust=TrustLevel.VERIFIED)
print(len(verified))  # 1

# Query by age (last 5 minutes)
recent = ledger.query(max_age_seconds=300)

# Query by source
from_analyst = ledger.query(source="analyst")

# Convert to Messages for pattern consumption
messages = ledger.to_messages()              # all items
messages = ledger.to_messages(max_tokens=500)  # budget-constrained (most recent first)

# Snapshot for persistence
snap = ledger.snapshot()                     # JSON-serializable dict
restored = ContextLedger.from_snapshot(snap)
```

## Three-Tier Memory

### WorkingMemory — Bounded In-Flight Context

```python
from pyagent_context import WorkingMemory, ContextItem

wm = WorkingMemory(max_items=50, max_tokens=10_000)

item = ContextItem(content="New observation", source="agent_1")
evicted = wm.add(item)  # returns list of evicted items if capacity exceeded

print(len(wm))            # current item count
print(wm.total_tokens)    # current token usage
print(f"{wm.utilization:.0%}")  # e.g. "42%"
```

### SessionMemory — Persist Across Turns

```python
from pyagent_context import SessionMemory, ContextItem

# JSON backend (simple, human-readable)
session = SessionMemory("user-123-session", backend="json", storage_path=".sessions")
session.add(ContextItem(content="User prefers concise answers", source="user"))
session.save()

# Later: reload
session2 = SessionMemory("user-123-session", backend="json", storage_path=".sessions")
session2.load()
items = session2.get_all()

# SQLite backend (concurrent-safe)
session = SessionMemory("user-123-session", backend="sqlite", storage_path=".sessions")
session.add(ContextItem(content="Important context", source="system"))
session.save()
```

### SemanticMemory — Vector-Indexed Long-Term Store

```python
from pyagent_context import InMemorySemanticStore, ContextItem

store = InMemorySemanticStore()

# Index items
store.add(ContextItem(content="Python asyncio event loop concurrency patterns", source="docs"))
store.add(ContextItem(content="JavaScript React component lifecycle hooks", source="docs"))
store.add(ContextItem(content="Python FastAPI async web framework REST API design", source="docs"))

# Semantic search (TF-IDF cosine similarity)
results = store.search("Python async web", top_k=3)
for r in results:
    print(f"  [{r.score:.2f}] {r.item.content[:60]}...")

# Remove / clear
store.remove(item_id)
store.clear()
```

## ContextCompressor — Manage Token Growth

Four policies: `NONE`, `FIFO`, `SEMANTIC_LOSSLESS`, `SAWTOOTH`.

```python
from pyagent_context import ContextCompressor, CompressionPolicy, ContextLedger

# FIFO: drop oldest items until under floor
compressor = ContextCompressor(
    policy=CompressionPolicy.FIFO,
    threshold_tokens=10_000,   # trigger compression at 10k tokens
    floor_tokens=5_000,        # compress down to 5k
)

if compressor.should_compress(ledger):
    compressed = compressor.compress(ledger)
    print(f"Compressed: {ledger.total_tokens} → {compressed.total_tokens} tokens")

# SAWTOOTH: compress to floor, then allow growth again
compressor = ContextCompressor(
    policy=CompressionPolicy.SAWTOOTH,
    threshold_tokens=10_000,
    floor_tokens=3_000,
)

# SEMANTIC_LOSSLESS: compress text but preserve verified items unchanged
compressor = ContextCompressor(
    policy=CompressionPolicy.SEMANTIC_LOSSLESS,
    threshold_tokens=8_000,
    floor_tokens=4_000,
)
```

## TrustAwareRetriever — Smart Context Selection

Scores items by `trust × recency × relevance`:

```python
from pyagent_context import TrustAwareRetriever

retriever = TrustAwareRetriever(
    weight_trust=0.3,
    weight_recency=0.3,
    weight_relevance=0.4,
    recency_half_life=3600.0,   # 1 hour half-life
)

results = retriever.retrieve(ledger, "Q3 earnings revenue growth", top_k=5)
for r in results:
    print(f"  [{r.score:.2f}] trust={r.trust_score:.2f} "
          f"recency={r.recency_score:.2f} relevance={r.relevance_score:.2f}")
    print(f"    {r.item.content[:80]}...")
```

## ContextLifecycle — Expiry, Decay, Consolidation

```python
from pyagent_context import ContextLifecycle

lifecycle = ContextLifecycle(consolidation_threshold=0.6)

# Remove expired items
new_ledger, expired = lifecycle.sweep_expired(ledger)
print(f"Removed {len(expired)} expired items")

# Apply freshness decay (old items get smaller token budgets)
decayed = lifecycle.apply_freshness_decay(ledger, half_life_seconds=3600)

# Merge similar items from the same source
consolidated = lifecycle.consolidate(ledger)
print(f"Consolidated: {len(ledger)} → {len(consolidated)} items")
```

## ContextRedactor — Sensitivity-Based Redaction

```python
from pyagent_context import ContextRedactor
from pyagent_context.item import Sensitivity

# Redact items above INTERNAL sensitivity
redactor = ContextRedactor(
    max_sensitivity=Sensitivity.INTERNAL,
    redaction_text="[REDACTED — CONFIDENTIAL]",
)

redacted_ledger = redactor.redact_ledger(ledger)

# Or exclude entirely instead of redacting
redactor = ContextRedactor(
    max_sensitivity=Sensitivity.INTERNAL,
    exclude_above=True,
)
filtered_ledger = redactor.redact_ledger(ledger)
```

## Integration with pyagent-patterns

```python
from pyagent_patterns.base import Agent, MockLLM
from pyagent_patterns.orchestration import Pipeline
from pyagent_context import ContextLedger, TrustLevel, WorkingMemory

ledger = ContextLedger()

# Before pattern run: seed with trusted context
ledger.add("User is asking about Q3 2025 earnings", "user", TrustLevel.USER_PROVIDED)
ledger.add("Tesla Q3 revenue was $25.2B", "database", TrustLevel.VERIFIED)

# Convert to messages and prepend to pattern input
context_messages = ledger.to_messages(max_tokens=2000)

# After pattern run: store results
ledger.add(result.output, "pipeline", TrustLevel.INFERRED)
```

## Full Documentation

See [pyagent.dev](https://pyagent.dev) for full API reference and integration guides.
