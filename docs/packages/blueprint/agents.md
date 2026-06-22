---
description: "Define agents in a PyAgent blueprint — providers, prompts, tools, and per-agent configuration."
---

# Blueprint — Agents

Each entry under `agents:` defines a named agent that can be referenced in workflows.

---

## AgentSpec Fields

```yaml
agents:
  my_agent:
    provider: fast          # Required if providers: block exists
    description: "..."      # Human-readable, shown in Studio /agents view
    prompt: |               # System prompt injected before every call
      ...
    tools: []               # Tool names — must be registered at compile time
    guardrails: []          # Guardrail refs — applied before output is returned
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `provider` | string | `""` | Key from the `providers:` block |
| `description` | string | `""` | Shown in Studio /agents panel |
| `prompt` | string | required | System prompt for this agent |
| `tools` | list[string] | `[]` | Registered tool names |
| `guardrails` | list[string] | `[]` | Registered guardrail names |

---

## Prompts

Prompts are system-level instructions prepended to every call. Keep them role-focused:

```yaml
agents:
  classifier:
    prompt: |
      Classify the customer message into exactly one of:
      billing, technical, returns, general.
      Respond with ONLY the category name.

  billing_agent:
    prompt: |
      You are a billing specialist. Handle disputes, refunds, and
      subscription questions.

      Rules:
      1. Acknowledge the customer's frustration first.
      2. Confirm the charge details before offering a resolution.
      3. Always provide a concrete next step with a timeline.

  formatter:
    prompt: |
      Format the input as a professional customer service response.
      - Remove any internal notes or agent reasoning.
      - Keep the response under 200 words.
      - End with a friendly closing line.
```

### Prompt templating

Prompts are plain strings — no special templating syntax. Inject dynamic data at runtime by passing it in the task string or via a context ledger wired through the compiler.

---

## Providers

Each agent references a named provider from the `providers:` block. A fast cheap model for simple tasks, an expert model for complex ones:

```yaml
providers:
  fast:
    provider: anthropic
    model: claude-haiku-3-5-20241022
    max_tokens: 512
  expert:
    provider: anthropic
    model: claude-sonnet-4-20250514
    max_tokens: 2048

agents:
  classifier:
    provider: fast      # Cheap — just classifies
  billing_agent:
    provider: expert    # Expensive — handles real edge cases
  formatter:
    provider: fast      # Cheap — just reformats
```

If no `providers:` block is defined, all agents use `MockLLM` — ideal for unit tests.

---

## Tools

Tools listed here must be registered in the `ProviderRegistry` (or passed to `BlueprintCompiler`) at runtime. The blueprint declares intent; the compiler wires the actual callables.

```yaml
agents:
  billing_agent:
    tools: [lookup_invoice, issue_refund, send_email]
```

```python
from pyagent_blueprint import BlueprintCompiler

compiler = BlueprintCompiler(
    tools={
        "lookup_invoice": my_lookup_fn,
        "issue_refund":   my_refund_fn,
        "send_email":     my_email_fn,
    }
)
graph = compiler.compile(spec)
```

The `BlueprintValidator` will raise an error if a tool name is listed in an agent spec but not registered with the compiler.

---

## Guardrails

Like tools, guardrail names are resolved at compile time. Guardrails run after the agent produces output and before it is returned to the caller.

```yaml
agents:
  public_facing_agent:
    guardrails: [no_pii, max_length_400, tone_check]
```

```python
compiler = BlueprintCompiler(
    guardrails={
        "no_pii":         pii_redaction_guard,
        "max_length_400": length_guard(400),
        "tone_check":     tone_guard,
    }
)
```

---

## Agent Descriptions in Studio

The `description` field powers the Studio `/agents` panel — it shows each agent's role alongside its full prompt, provider, and tool list. Use it to describe the agent's responsibility in one sentence.

```yaml
agents:
  classifier:
    description: "Route incoming messages to billing, technical, returns, or general agents"
  billing_agent:
    description: "Handle billing disputes, refund requests, and subscription changes"
```

---

## See Also

- [Workflows](workflows.md) — how agents are wired into patterns
- [Providers](providers.md) — model and token configuration
- [Contracts](contracts.md) — per-agent input/output validation
- [Full Spec Reference](spec-format.md)
