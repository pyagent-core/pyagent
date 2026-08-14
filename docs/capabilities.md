---
description: "Every PyAgent package's real capabilities, published as structured JSON at /capabilities.json — Blueprint's 9 RuntimeAdapters, Router's model selection, Context's memory tiers, Trace's exporters, Compress's budget tools, Providers' routing strategies, and Studio's CLI."
---

# Capability catalog

[pyagent.org/patterns.json](patterns.json) covers the 18 named orchestration patterns in
`pyagent-patterns`. Everything else PyAgent ships — the other 8 packages — has its own
machine-readable catalog at **[pyagent.org/capabilities.json](capabilities.json)**, generated from
`data/capabilities.yml` so it can't drift from this page or from the per-package docs.

## What's in it

| Package | What's cataloged |
|---|---|
| [`pyagent-blueprint`](packages/blueprint/index.md) | All 9 `RuntimeAdapter`s (`pyagent`, `single_agent`, `sequential_chain`, `state_machine`, `simple_loop`, `langgraph`, `crewai`, `openai_agents`, `semantic_kernel`) with execution model, exercised capability, and install command for each |
| [`pyagent-patterns`](packages/patterns/index.md) | Pointer to the dedicated `patterns.json` catalog |
| [`pyagent-router`](packages/router.md) | `DifficultyScorer`, `ModelSelector`, `CostEstimator`, `RouterMiddleware` |
| [`pyagent-context`](packages/context.md) | Three memory tiers (`WorkingMemory`, `SessionMemory`, `SemanticMemoryProtocol`) plus `ContextLedger`, `TrustLevel`, `Sensitivity`, `ContextRedactor`, `TrustAwareRetriever`, `CompressionPolicy` |
| [`pyagent-trace`](packages/trace.md) | Four exporters (`console`, `jsonl`, `otel`, `langfuse`) plus `TraceEventBus`, `Recorder`, `CostTracker`, `PatternSpanEmitter` |
| [`pyagent-compress`](packages/compress.md) | `TokenBudget`, `MessageCompressor`, `AgentPruner`, `InteractionPruner`, `CompressMiddleware` |
| [`pyagent-providers`](packages/providers.md) | Four routing strategies (`capability_first`, `cost_first`, `latency_first`, `round_robin`) plus `ProviderRegistry`, `ProviderRouter`, `FallbackChain`, `CapabilityNegotiator`, `CostOptimizer` |
| [`pyagent-studio`](packages/studio/index.md) | Full CLI surface (`apply`, `get`, `validate`, `test`, `diff`, `simulate`, `render`, `generate`, `providers list`, `providers health`, `describe`, `dashboard`) plus the web dashboard's capabilities |
| `pyagent-all` | Meta-package pointer |

Every id/class/CLI-command name in the catalog is copied verbatim from that package's real public
API (`__all__` in its `__init__.py`) or its CLI's actual `@command` names — not invented or
aspirational. See `data/capabilities.yml`'s header for the grounding rule, and
`aeo/scripts/validate_capabilities_catalog.py` for the automated check that it hasn't drifted from
either the source YAML or the real `packages/` directory.

Beyond the pattern catalog, most capability entries also carry `use_when`/`avoid_when`/`tradeoffs`
fields — the same decision-guidance shape `patterns.json` already had, extended to the non-pattern
capabilities (memory tiers, routing strategies, exporters, and so on) that previously had none.

## Why two files instead of one

`patterns.json`'s pattern objects (`use_when`/`avoid_when`/`pairs_with`) and `capabilities.json`'s
package objects (`routing_strategies`/`memory_tiers`/`exporters`/`cli_commands`) are different
enough shapes that merging them into one schema would make both harder to consume. `capabilities.json`
links back to `patterns.json` via its own `see_also` field, so a tool only needs one starting URL.
