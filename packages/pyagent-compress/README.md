# pyagent-compress

**Inter-agent message compression and token budget management** for multi-agent LLM systems. Reduce token costs without losing key information.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](../../LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

## Install

```bash
pip install pyagent-compress
```

Depends on: `pyagent-patterns`.

## Why Compression?

In long pipelines, verbose intermediate outputs compound quickly — 5 stages × 2000 tokens each = 10,000 tokens of context consumed before the final stage starts. `pyagent-compress` strips filler, ranks sentences by information density, and enforces hard token budgets — so downstream agents work with dense, high-signal context.

---

## Components

- **MessageCompressor** — Reduce message size by removing filler and ranking sentences
- **CompressMiddleware** — Auto-compress agent outputs before passing to the next stage
- **TokenBudget** — Enforce per-agent and per-workflow token limits
- **AgentPruner** — Detect agents that are repeating others rather than adding value
- **InteractionPruner** — Detect early consensus and skip remaining rounds

---

## MessageCompressor — compress individual messages

```python
from pyagent_compress import MessageCompressor

# Default: 50% target compression
compressor = MessageCompressor(target_ratio=0.5)

# Aggressive: 30% target
compressor = MessageCompressor(
    target_ratio=0.3,
    min_sentence_length=20,   # drop very short sentences
    remove_filler=True,        # strip "let me think", "basically", "in other words", etc.
)

verbose_output = """
Let me think about this carefully. Okay so basically what we have here is a situation
where the system needs to handle concurrent writes. In other words, we need to think
about race conditions. I believe that the most important thing is to use transactions.
The system should implement SERIALIZABLE isolation level because it ensures that all
transactions are executed as if they were serial. Studies show that this prevents 100%
of dirty reads. The database must also use row-level locking. Additionally, we need
retry logic for deadlock situations, with exponential backoff starting at 10ms.
Finally, the application should use connection pooling with a maximum of 20 connections.
"""

result = compressor.compress(verbose_output)
print(result.compressed)                    # key sentences, filler removed
print(f"Saved: {result.savings_pct:.0%}")  # e.g. "Saved: 47%"
print(result.original_tokens)              # 120
print(result.compressed_tokens)            # 64
```

---

## CompressMiddleware — wrap agents with automatic compression

```python
from pyagent_compress import CompressMiddleware, MessageCompressor
from pyagent_patterns.orchestration import Pipeline

# Compress outputs from intermediate stages — let the final stage see full output
compressor = MessageCompressor(target_ratio=0.4)
middleware = CompressMiddleware(compressor=compressor)

pipeline = Pipeline(stages=[
    middleware.wrap(Agent("researcher", llm, system_prompt="Research thoroughly. "
                                                            "Include all relevant details.")),
    middleware.wrap(Agent("analyst",    llm, system_prompt="Analyse the research findings.")),
    # Final stage: no compression — we want the full output
    Agent("writer", OpenAILLM("gpt-4o"), system_prompt="Write the final report."),
])

result = asyncio.run(pipeline.run("Research and analyse quantum computing hardware trends"))

# Check compression stats from wrapped agents
for stage in pipeline._stages[:2]:
    if hasattr(stage, "compression_log"):
        for entry in stage.compression_log:
            print(f"{stage.name}: saved {entry['savings_pct']:.0%} "
                  f"({entry['original_tokens']} → {entry['compressed_tokens']} tokens)")
```

---

## TokenBudget — enforce workflow-wide token limits

```python
from pyagent_compress import TokenBudget, CompressMiddleware

# Set a 50k total token budget, 10k per agent
budget = TokenBudget(
    workflow_limit=50_000,
    per_agent_limit=10_000,
    strict=True,    # raises BudgetExceeded if exceeded; False = track only
)

middleware = CompressMiddleware(budget=budget)

# Custom per-agent limits
budget.register_agent("researcher", limit=15_000)   # researcher gets more budget
budget.register_agent("writer",     limit=5_000)    # writer gets less

print(budget.remaining())               # 50000 (workflow remaining)
print(budget.remaining("researcher"))   # 15000 (researcher remaining)

# After running some agents:
print(budget.total_used)                # tokens consumed so far
print(budget.workflow_utilization)      # 0.34 → 34% of budget used
print(budget.summary())
# {
#   "workflow": {"limit": 50000, "used": 17000, "remaining": 33000, "utilization": 0.34},
#   "researcher": {"limit": 15000, "used": 12000, "remaining": 3000, "utilization": 0.80},
#   ...
# }
```

---

## AgentPruner — detect non-contributing agents

```python
from pyagent_compress import AgentPruner, InteractionPruner

# Detect agents that are repeating others rather than adding value
pruner = AgentPruner(
    min_contribution=0.3,   # agents scoring below 0.3 should be pruned
    window_size=5,          # look at last 5 messages per agent
)

# After running a multi-agent pattern:
scores = pruner.score_agents(result.messages, task="Design a distributed cache")
for score in scores:
    print(f"{score.agent_name}: {score.score:.2f} "
          f"(unique info: {score.unique_info:.2f}, messages: {score.message_count})")
# analyst_1: 0.72 (unique info: 0.65, messages: 3)
# analyst_2: 0.18 (unique info: 0.08, messages: 3)  ← prune this one
# analyst_3: 0.61 (unique info: 0.54, messages: 3)

agents_to_prune = pruner.should_prune(scores)
print(f"Prune: {agents_to_prune}")   # ["analyst_2"]

# Detect early consensus to skip remaining rounds
interaction_pruner = InteractionPruner(
    consensus_threshold=0.7,   # 70% similarity = consensus reached
    min_rounds=1,              # always run at least 1 round
)

if interaction_pruner.has_consensus(current_round_outputs, current_round=2):
    print("Consensus reached — skipping remaining rounds")
```

---

## Full Documentation

See [pyagent.dev](https://pyagent.dev) for full API reference and integration guides.
