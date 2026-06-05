# pyagent-compress

**Inter-agent message compression and token budget management** for multi-agent LLM systems. Reduce token costs without losing key information.

## Install

```bash
pip install pyagent-compress
```

## Components

- **MessageCompressor** — Reduce message size by removing filler and ranking sentences
- **AgentPruner** — Detect and remove non-contributing agents
- **InteractionPruner** — Detect consensus and prune redundant rounds
- **TokenBudget** — Enforce per-agent and per-workflow token limits
- **CompressMiddleware** — Auto-compress agent outputs

## Quick Example

```python
from pyagent_compress import MessageCompressor, TokenBudget

compressor = MessageCompressor(target_ratio=0.5)
result = compressor.compress("Let me think about this... Basically, revenue grew 15%.")
print(f"Savings: {result.savings_pct:.0%}")

budget = TokenBudget(workflow_limit=50_000, per_agent_limit=10_000)
budget.consume("agent_a", 3000)
```
