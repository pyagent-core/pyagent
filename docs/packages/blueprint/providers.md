# Blueprint — Providers

The `providers:` block declares the LLM provider bindings available to agents in this blueprint. Agents reference these by name — the compiler resolves them to real provider instances at runtime.

---

## ProviderBindingSpec Fields

```yaml
providers:
  my_provider:
    provider: anthropic       # 'anthropic' | 'openai' | custom key
    model: claude-sonnet-4-20250514
    max_tokens: 2048
    timeout_seconds: 60.0
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `provider` | string | required | Provider backend key |
| `model` | string | required | Model identifier |
| `max_tokens` | int | `1024` | Maximum output tokens |
| `timeout_seconds` | float | `null` | Per-call timeout; null = no limit |

---

## Model Tier Pattern

The most common pattern is defining two or three tiers and assigning agents to the cheapest tier that can handle their task:

```yaml
providers:
  fast:
    provider: anthropic
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

agents:
  classifier:  { provider: fast,     prompt: "Classify into one of: ..." }
  formatter:   { provider: fast,     prompt: "Format the response." }
  analyst:     { provider: balanced, prompt: "Analyse the data." }
  strategist:  { provider: expert,   prompt: "Design the long-term strategy." }
```

A `classifier` that just outputs a single word costs a fraction of a cent. Routing it through `expert` would be 10–50× more expensive with no quality benefit.

---

## Multi-Provider Setup

Mix providers across tiers — Anthropic for quality-sensitive work, OpenAI for cost-sensitive work:

```yaml
providers:
  claude_fast:
    provider: anthropic
    model: claude-haiku-3-5-20241022
    max_tokens: 512

  claude_expert:
    provider: anthropic
    model: claude-sonnet-4-20250514
    max_tokens: 4096

  openai_mini:
    provider: openai
    model: gpt-4o-mini
    max_tokens: 1024

  openai_full:
    provider: openai
    model: gpt-4o
    max_tokens: 2048
```

---

## Wiring Providers at Compile Time

The `provider` key in a binding refers to a backend registered with the `ProviderRegistry`. The compiler resolves names at compile time:

```python
from pyagent_blueprint import load_blueprint, BlueprintCompiler
from pyagent_providers import ProviderRegistry, AnthropicLLM, OpenAILLM

registry = ProviderRegistry()
registry.register("anthropic", AnthropicLLM)
registry.register("openai",    OpenAILLM)

spec   = load_blueprint("blueprint.yaml")
graph  = BlueprintCompiler(provider_registry=registry).compile(spec)
```

If a provider backend key in the YAML is not registered, `BlueprintValidator` raises an error before compilation.

---

## MockLLM for Testing

Omit the `providers:` block entirely (or omit the `provider_registry` argument) and the compiler uses `MockLLM` — deterministic, free, and fast:

```yaml
# test-blueprint.yaml — no providers block
api_version: pyagent/v1
metadata:
  name: test
  version: "1.0.0"
agents:
  responder:
    prompt: "Answer questions."
workflows:
  main:
    pattern: pipeline
    agents:
      stages: [responder]
```

```python
spec  = load_blueprint("test-blueprint.yaml")
graph = BlueprintCompiler().compile(spec)   # Uses MockLLM automatically
```

---

## Provider Health in Studio

Providers defined in the blueprint appear in Studio's `/providers` dashboard — health status, average latency, p99 latency, error rate, and budget usage. See [Studio Dashboard](../studio/dashboard.md#providers).

---

## See Also

- [Agents](agents.md) — assigning providers to agents
- [Workflows](workflows.md) — `fallback_provider` in recovery config
- [Providers Package](../providers.md) — `ProviderRegistry`, `FallbackChain`, `CostOptimizer`
- [Full Spec Reference](spec-format.md)
