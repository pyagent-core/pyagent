---
description: "pyagent-context — three-tier memory (working, session, semantic) shared across agents with trust and PII controls."
---

# pyagent-context

**Three-tier memory with trust-aware context ledger** — working memory for a single run, session memory across turns, and semantic memory for long-term recall. Agents share context without overloading LLM context windows.

```bash
pip install pyagent-context                   # Core (working + session memory)
pip install pyagent-context[compress]         # + ContextCompressor
pip install pyagent-context[chromadb]         # + ChromaDB semantic backend
```

---

## Architecture

```mermaid
flowchart TD
    A[Agent] --> WM[WorkingMemory\nbounded deque, evicts oldest]
    A --> SM[SessionMemory\nJSON or SQLite, persists across turns]
    A --> SEM[SemanticMemory\nChromaDB, vector similarity search]
    WM --> CL[ContextLedger\nappend-only log, query by trust]
    SM --> CL
    SEM --> CL
    CL --> MSG[to_messages(max_tokens=)\nconvert to LLM message list]
```

**Three tiers:**

| Tier | Class | Scope | Backend |
|------|-------|-------|---------|
| Working | `WorkingMemory` | Single pattern run | In-memory deque |
| Session | `SessionMemory` | Multi-turn conversation | JSON file or SQLite |
| Semantic | `SemanticMemory` | Long-term recall | ChromaDB (vector) |

---

## Core Concept — ContextItem

Every piece of memory is a `ContextItem` — content plus trust metadata.

```python
from pyagent_context.item import ContextItem, TrustLevel

item = ContextItem(
    content="Customer prefers email communication, timezone UTC+5:30",
    source="crm_agent",
    trust_level=TrustLevel.VERIFIED,   # VERIFIED > INFERRED > SPECULATIVE
)

print(item.id)              # UUID
print(item.token_estimate)  # rough token count
print(item.timestamp)       # creation time (float)
print(item.to_dict())       # serialize to JSON-compatible dict
```

`TrustLevel` controls what agents can rely on:

| Level | Meaning | Example |
|-------|---------|---------|
| `VERIFIED` | Confirmed by a reliable source | DB lookup, user-provided |
| `INFERRED` | Derived by an agent — probably right | LLM classification result |
| `SPECULATIVE` | Agent's guess — use with caution | Predicted intent |

---

## Tier 1 — WorkingMemory

Bounded deque for a single run. Automatically evicts the oldest items when capacity (count or tokens) is exceeded.

```python
from pyagent_context.memory.working import WorkingMemory
from pyagent_context.item import ContextItem, TrustLevel

wm = WorkingMemory(max_items=50, max_tokens=20_000)

# Add items — eviction happens automatically
wm.add(ContextItem(content="User asked about Q3 revenue", source="input"))
wm.add(ContextItem(content="Extractor found: $25.2B revenue", source="extractor_agent"))
wm.add(ContextItem(content="Fact check: VERIFIED", source="fact_checker", trust_level=TrustLevel.VERIFIED))

print(f"Items: {len(wm)}")
print(f"Tokens: {wm.total_tokens}")
print(f"Utilization: {wm.utilization:.1%}")

# Eviction returns what was dropped
evicted = wm.add(ContextItem(content="new item", source="agent_x"))
if evicted:
    print(f"Evicted {len(evicted)} item(s) to stay within budget")
```

### Use in a Pipeline stage

```python
import asyncio
from pyagent_patterns.base import Agent, Message
from pyagent_patterns.orchestration import Pipeline
from pyagent_context.memory.working import WorkingMemory
from pyagent_context.item import ContextItem
from pyagent_providers import AnthropicLLM

wm = WorkingMemory(max_tokens=10_000)

async def run_with_memory(task: str) -> str:
    # Seed working memory with prior context
    wm.add(ContextItem(content=f"User goal: {task}", source="user"))

    pipeline = Pipeline(stages=[
        Agent("extractor", AnthropicLLM("claude-haiku-3-5-20241022"),
              system_prompt="Extract key claims and figures."),
        Agent("analyst",   AnthropicLLM("claude-sonnet-4-20250514"),
              system_prompt="Analyze the extracted data and give a recommendation."),
    ])

    result = await pipeline.run(task)

    # Store the result back into working memory
    wm.add(ContextItem(content=result.output, source="pipeline", trust_level=ContextItem.INFERRED))
    print(f"Memory: {len(wm)} items, {wm.total_tokens} tokens")
    return result.output

asyncio.run(run_with_memory("Analyze Tesla Q3 2025 earnings"))
```

---

## Tier 2 — SessionMemory

Persists across turns — store conversation history so agents remember prior interactions.

```python
from pyagent_context.memory.session import SessionMemory
from pyagent_context.item import ContextItem, TrustLevel

# JSON backend (simple, default)
session = SessionMemory(session_id="user-42-support-ticket-991", backend="json")

# Add items during turn 1
session.add(ContextItem(content="User reported: API returns 429 on /v2/search", source="user_turn_1"))
session.add(ContextItem(content="Agent diagnosed: rate limit exceeded, quota 1000/min", source="agent_turn_1",
                        trust_level=TrustLevel.INFERRED))
session.save()   # persist to disk

# ---- next turn / new process ----

session2 = SessionMemory(session_id="user-42-support-ticket-991", backend="json")
history = session2.get_all()   # load all prior items

print(f"Prior turns: {len(history)} items")
for item in history:
    print(f"  [{item.trust_level}] {item.source}: {item.content[:60]}")
```

### SQLite backend for concurrent multi-agent access

```python
# Multiple agents writing to the same session safely
session = SessionMemory(
    session_id="team-analysis-run-001",
    backend="sqlite",
    storage_path=".sessions",
)

session.add(ContextItem(content="bull_agent: Strong revenue growth supports premium", source="bull_agent"))
session.add(ContextItem(content="bear_agent: P/E 45x unsustainable", source="bear_agent"))
session.save()
```

---

## Tier 3 — ContextLedger

Append-only log with trust-aware querying and token-budget-aware message conversion.

```python
from pyagent_context.ledger import ContextLedger
from pyagent_context.item import ContextItem, TrustLevel

ledger = ContextLedger()

# Add items with different trust levels
ledger.add("User is a senior developer", source="profile_agent", trust_level=TrustLevel.VERIFIED)
ledger.add("User prefers concise answers", source="style_inference", trust_level=TrustLevel.INFERRED)
ledger.add("User may be frustrated", source="sentiment_agent", trust_level=TrustLevel.SPECULATIVE)

# Query by trust — only act on verified and inferred context
reliable = ledger.query(min_trust=TrustLevel.INFERRED)
print(f"Reliable context items: {len(reliable)}")

# Query by recency
recent = ledger.query(max_age_seconds=300)   # last 5 minutes

# Query by source
from_profile = ledger.query(source="profile_agent")

# Convert to messages with token budget for LLM injection
messages = ledger.to_messages(max_tokens=2000)  # most recent first, within budget
print(f"Injecting {len(messages)} context messages ({ledger.total_tokens} total tokens)")

# Snapshot for persistence
snapshot = ledger.snapshot()
restored = ContextLedger.from_snapshot(snapshot)
```

### Inject ledger context into an agent call

```python
from pyagent_patterns.base import Agent, Message
from pyagent_providers import AnthropicLLM

ledger = ContextLedger()
ledger.add("User is CFO at a 500-person SaaS company", source="crm", trust_level=TrustLevel.VERIFIED)
ledger.add("User asked about churn forecasting last week", source="history", trust_level=TrustLevel.VERIFIED)

agent = Agent("advisor", AnthropicLLM("claude-sonnet-4-20250514"),
              system_prompt="You are a financial advisor. Use the provided context.")

# Build messages: context first, then the actual query
context_messages = ledger.to_messages(max_tokens=1500)
query = Message.user("What's the best way to reduce churn in our enterprise tier?")

import asyncio
result = asyncio.run(agent.run_messages([*context_messages, query]))
print(result.output)
```

### Hook Integration — Automatic Context Wiring

The hook system wires a `ContextLedger` directly into an agent: the agent reads context before each LLM call and writes its output back to the ledger automatically — no manual `to_messages()` needed.

```python
import asyncio
from pyagent_context.ledger import ContextLedger
from pyagent_context.item import ContextItem, TrustLevel
from pyagent_patterns.base import Agent
from pyagent_providers import AnthropicLLM

ledger = ContextLedger()
ledger.add("User is CFO at a 500-person SaaS company", source="crm", trust_level=TrustLevel.VERIFIED)
ledger.add("User asked about churn forecasting last week", source="history", trust_level=TrustLevel.VERIFIED)

agent = (
    Agent("advisor", AnthropicLLM("claude-sonnet-4-20250514"),
          system_prompt="You are a financial advisor. Use the provided context.")
    .set_context(ledger)   # reads ledger before LLM call; writes output back after
)

result = asyncio.run(agent.run("What's the best way to reduce churn in our enterprise tier?"))
print(result.output)
print(f"Ledger now has {len(ledger)} items")  # original 2 + agent output = 3
```

To wire context on all agents in a blueprint at once:

```python
from pyagent_blueprint import load_blueprint, BlueprintCompiler

graph = BlueprintCompiler().compile(load_blueprint("blueprint.yaml"))
graph.wire_context(ledger)   # sets context hook on every agent in the graph
```

→ See the full [Hooks Guide](../guides/hooks.md) for all four hook types.

---

## SemanticMemory (ChromaDB)

Long-term recall via vector similarity — retrieve the most relevant past context, not just the most recent.

```bash
pip install pyagent-context[chromadb]
```

```python
from pyagent_context.memory.semantic import SemanticMemory
from pyagent_context.item import ContextItem, TrustLevel

# Persistent collection backed by ChromaDB
sem = SemanticMemory(collection_name="agent_knowledge_base", persist_directory=".chromadb")

# Add domain knowledge
sem.add(ContextItem(content="PCI-DSS v4 requires tokenization of all cardholder data at rest",
                    source="compliance_docs", trust_level=TrustLevel.VERIFIED))
sem.add(ContextItem(content="SOC2 Type II audit completed 2024-11, no critical findings",
                    source="audit_report", trust_level=TrustLevel.VERIFIED))
sem.add(ContextItem(content="Customer XYZ has a data residency requirement: EU only",
                    source="crm", trust_level=TrustLevel.VERIFIED))

# Retrieve by semantic similarity
results = sem.search("What are our data compliance requirements?", top_k=3)
for item, score in results:
    print(f"[{score:.2f}] {item.content[:80]}")

# Combine with ledger
ledger = ContextLedger(items=results[0])  # inject top semantic results
```

---

## ContextCompressor

When the ledger grows beyond the LLM's context window, compress older items while preserving high-trust content.

```bash
pip install pyagent-context[compress]
```

```python
from pyagent_context.compression import ContextCompressor
from pyagent_context.ledger import ContextLedger
from pyagent_context.item import TrustLevel

compressor = ContextCompressor(target_tokens=4000)

# Ledger with 12k tokens of history
large_ledger = ContextLedger(items=long_history)

# Compress: summarize SPECULATIVE items, keep VERIFIED intact
compressed = compressor.compress(large_ledger)
print(f"Compressed: {large_ledger.total_tokens} → {compressed.total_tokens} tokens")
print(f"Verified items preserved: all")
```

---

## Redaction

Strip PII before items leave the trust boundary.

```python
from pyagent_context.redaction import Redactor

redactor = Redactor(patterns=["email", "phone", "credit_card", "ssn"])

safe = redactor.redact("Contact john.doe@acme.com or call +1-555-867-5309")
print(safe)
# → "Contact [EMAIL] or call [PHONE]"
```

---

## Full Example — Multi-Turn Customer Support Agent

```python
import asyncio
from pyagent_context.ledger import ContextLedger
from pyagent_context.memory.session import SessionMemory
from pyagent_context.item import ContextItem, TrustLevel
from pyagent_patterns.base import Agent, Message
from pyagent_providers import AnthropicLLM

SESSION_ID = "support-ticket-4421"

async def handle_turn(user_message: str) -> str:
    # Load prior session
    session = SessionMemory(session_id=SESSION_ID, backend="sqlite")
    ledger = ContextLedger(items=session.get_all())

    # Add verified facts about the user (from CRM, set once)
    if len(ledger) == 0:
        ledger.add("User: Enterprise customer, plan: Pro, billing monthly",
                   source="crm", trust_level=TrustLevel.VERIFIED)

    # Add this turn's input
    ledger.add(user_message, source="user", trust_level=TrustLevel.VERIFIED)

    agent = Agent(
        "support_agent",
        AnthropicLLM("claude-sonnet-4-20250514"),
        system_prompt="You are a helpful support agent. Use prior context to avoid repetition.",
    )

    context_msgs = ledger.to_messages(max_tokens=3000)
    result = await agent.run_messages([*context_msgs, Message.user(user_message)])

    # Persist agent response back to session
    ledger.add(result.output, source="agent", trust_level=TrustLevel.INFERRED)
    session._items = ledger.items
    session.save()

    return result.output

# Simulated multi-turn conversation
for msg in ["I can't access my dashboard", "I already tried reloading", "Same issue on mobile too"]:
    reply = asyncio.run(handle_turn(msg))
    print(f"User: {msg}\nAgent: {reply}\n")
```

---

## When to Use Which Tier

| Situation | Use |
|-----------|-----|
| Single pattern run, ephemeral context | `WorkingMemory` |
| Multi-turn chat / conversation history | `SessionMemory` |
| Domain knowledge, long-term recall | `SemanticMemory` (ChromaDB) |
| Trust-filtered context injection | `ContextLedger` |
| Token-budget enforcement | `ContextLedger.to_messages(max_tokens=)` |
| PII protection before LLM injection | `Redactor` |

---

## See Also

- [Compress Package](compress.md) — token budget enforcement between pattern stages
- [Trace Package](trace.md) — record agent interactions for replay and debugging
- [Blueprint Package](blueprint.md) — declare context config in YAML with `context:` block
- [API Reference](../api/context.md)

---

<!-- cookbook-backlinks:start -->

## Cookbook examples

Complete, runnable recipes that use this package — [browse the Cookbook](../cookbook/index.md):

- [Multi-agent clinical note summarizer](../cookbook/healthcare/clinical-summary.md)

[Browse the full Cookbook →](../cookbook/index.md)

<!-- cookbook-backlinks:end -->
