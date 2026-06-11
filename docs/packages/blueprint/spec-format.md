# Blueprint Spec Format

A blueprint is a single YAML document. Every section is optional except `api_version`, `metadata`, `agents`, and `workflows`.

---

## Full Reference

```yaml
# ─────────────────────────────────────────────────────────
# Top-level keys
# ─────────────────────────────────────────────────────────
api_version: pyagent/v1           # Required. Must be "pyagent/v1".

# ─── Metadata ────────────────────────────────────────────
metadata:
  name: customer-support           # Required. Unique identifier.
  version: "1.2.0"                 # Required. Semantic version string.
  description: "Multi-tier support system"
  owner: platform-team
  tags: [support, production]

# ─── Providers ───────────────────────────────────────────
providers:
  fast:
    provider: anthropic             # 'anthropic' | 'openai' | custom key
    model: claude-haiku-3-5-20241022
    max_tokens: 512
    timeout_seconds: 10.0
  balanced:
    provider: openai
    model: gpt-4o-mini
    max_tokens: 1024
  expert:
    provider: anthropic
    model: claude-sonnet-4-20250514
    max_tokens: 2048
    timeout_seconds: 60.0

# ─── Context ─────────────────────────────────────────────
context:
  memory:
    working_max_tokens: 20000      # In-process working memory limit
    session_backend: sqlite        # 'json' | 'sqlite'  (persist across turns)
    semantic_enabled: true         # Enable ChromaDB semantic search
  compression:
    policy: semantic_lossless      # none | fifo | semantic_lossless | sawtooth
    target_ratio: 0.6              # Compress to 60% of current size
    threshold_tokens: 15000        # Trigger compression above this
    floor_tokens: 5000             # Never compress below this
  redaction:
    max_sensitivity: internal      # public | internal | confidential | restricted
    exclude_above: false

# ─── Agents ──────────────────────────────────────────────
agents:
  classifier:
    provider: fast                 # References a key in providers:
    description: "Route to billing, technical, returns, or general"
    prompt: |
      Classify the customer message into exactly one of:
      billing, technical, returns, general.
      Respond with ONLY the category name.
    tools: []                      # Tool names (must be registered at runtime)
    guardrails: []                 # Guardrail refs

  billing_agent:
    provider: expert
    description: "Handle billing disputes"
    prompt: |
      You are a billing specialist. Handle disputes, refunds, and
      subscription questions. Always acknowledge frustration first.
    tools: [lookup_invoice, issue_refund]

  formatter:
    provider: fast
    description: "Format the final response"
    prompt: |
      Format the response professionally. Keep under 200 words.
      Add a friendly closing line.

# ─── Workflows ───────────────────────────────────────────
workflows:
  main:
    pattern: supervisor            # One of the registered pattern names
    agents:
      classifier: classifier       # Pattern-specific agent mapping
      routes:
        billing: billing_agent
        technical: technical_agent
        returns: returns_agent
        general: general_agent
      formatter: formatter
    config:
      default_route: general
    recovery:
      max_retries: 2
      timeout_seconds: 30.0
      fallback_provider: fast     # Use cheap model if primary fails

# ─── Contracts ───────────────────────────────────────────
contracts:
  response_length:
    type: max_length
    value: 400
  no_pii_in_response:
    type: regex_absent
    pattern: "\\b\\d{4}[- ]?\\d{4}[- ]?\\d{4}[- ]?\\d{4}\\b"

# ─── Observability ───────────────────────────────────────
observability:
  tracing:
    enabled: true
    record_to: traces/runs.jsonl  # Optional: path to emit .jsonl trace file
  cost_budget:
    daily_usd: 50.0               # Alert / hard-stop above this
```

---

## Metadata {#metadata}

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Unique identifier for this system |
| `version` | Yes | Semantic version (shown in Studio, used in diffs) |
| `description` | No | Human-readable description |
| `owner` | No | Team or person responsible |
| `tags` | No | Free-form labels for filtering |

---

## Section Details

Each section has its own detailed page:

- [Providers](providers.md) — model tiers, timeout, token limits
- [Agents](agents.md) — prompts, tools, guardrails
- [Workflows](workflows.md) — patterns, routing, recovery
- [Context](context.md) — memory, compression, redaction
- [Contracts & Observability](contracts.md) — SLA constraints, cost budgets, trace recording

---

## Minimal Blueprint

```yaml
api_version: pyagent/v1

metadata:
  name: minimal
  version: "1.0.0"

agents:
  responder:
    prompt: "You are a helpful assistant."

workflows:
  main:
    pattern: pipeline
    agents:
      stages: [responder]
```

When no `providers:` block is present the compiler uses `MockLLM` automatically — useful for unit tests and CI.

---

## Multi-Workflow Blueprint

A single YAML file can contain multiple named workflows, each using different patterns:

```yaml
workflows:
  quick_analysis:
    pattern: pipeline
    agents:
      stages: [fast_extractor, fast_writer]

  deep_analysis:
    pattern: fan_out_fan_in
    agents:
      agents: [fundamentals_agent, technicals_agent, sentiment_agent]
      aggregator: synthesis_agent
    config: {}

  adversarial_review:
    pattern: debate
    agents:
      agents: [bull_agent, bear_agent]
      judge: judge_agent
    config:
      rounds: 2
```

```python
graph = BlueprintCompiler().compile(spec)

quick = asyncio.run(graph.run("quick_analysis", task))
deep  = asyncio.run(graph.run("deep_analysis",  task))
```
