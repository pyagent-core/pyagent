# Context Guide

Structured context memory with trust metadata, three-tier storage, compression, and retrieval for LLM agent systems.

## Overview

`pyagent-context` provides a `ContextLedger` — an append-only log of `ContextItem` objects, each annotated with trust level and sensitivity metadata. Items flow through three memory tiers and can be compressed, retrieved by relevance, and redacted for safety.

## ContextItem

The atomic unit of context:

```python
from pyagent_context import ContextItem, TrustLevel, Sensitivity

item = ContextItem(
    content="The customer's account was created on 2024-01-15.",
    source="database",
    trust=TrustLevel.VERIFIED,
    sensitivity=Sensitivity.INTERNAL,
)
```

### TrustLevel

| Level | Description |
|-------|-------------|
| `VERIFIED` | Confirmed from authoritative source |
| `INFERRED` | Derived by agent reasoning |
| `USER_PROVIDED` | Supplied by end user |
| `UNVERIFIED` | Unknown provenance |

### Sensitivity

| Level | Description |
|-------|-------------|
| `PUBLIC` | Safe to expose |
| `INTERNAL` | Internal use only |
| `CONFIDENTIAL` | Restricted access |
| `PII` | Personally identifiable information |

## ContextLedger

Append-only log with querying:

```python
from pyagent_context import ContextLedger

ledger = ContextLedger()
ledger.append(item)
ledger.total_tokens()
messages = ledger.to_messages(budget=4000)
```

## Three-Tier Memory

### WorkingMemory
Bounded deque for current conversation turn:
```python
from pyagent_context import WorkingMemory
wm = WorkingMemory(max_items=20, max_tokens=8000)
```

### SessionMemory
Persisted across turns (JSON or SQLite backend):
```python
from pyagent_context import SessionMemory
sm = SessionMemory(backend="json", path="session.json")
```

### SemanticMemory
Vector-indexed for similarity search:
```python
from pyagent_context import InMemorySemanticStore
store = InMemorySemanticStore()
store.add(item)
results = store.search("billing question", top_k=3)
```

## Compression

Four policies for managing context window:

| Policy | Description |
|--------|-------------|
| `none` | No compression |
| `fifo` | Drop oldest items first |
| `semantic_lossless` | Preserve high-trust items, drop redundant |
| `sawtooth` | Aggressive then gradual (preserves verified) |

```python
from pyagent_context import ContextCompressor
compressor = ContextCompressor(policy="semantic_lossless")
compressed = compressor.compress(items, target_tokens=4000)
```

## Trust-Aware Retrieval

Score and rank items by trust, recency, and keyword relevance:

```python
from pyagent_context import TrustAwareRetriever
retriever = TrustAwareRetriever()
results = retriever.retrieve(items, query="billing", top_k=5)
```

## Lifecycle Management

Expiry sweeps, freshness decay, and consolidation:

```python
from pyagent_context import ContextLifecycle
lifecycle = ContextLifecycle()
lifecycle.sweep_expired(ledger)
lifecycle.apply_freshness_decay(ledger)
lifecycle.consolidate(ledger, similarity_threshold=0.8)
```

## Redaction

Filter items by sensitivity before sending to LLM:

```python
from pyagent_context import ContextRedactor
redactor = ContextRedactor(max_sensitivity=Sensitivity.INTERNAL)
safe_items = redactor.redact(items)  # PII items excluded
```

## API Reference

::: pyagent_context
