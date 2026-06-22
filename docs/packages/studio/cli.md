---
description: "The pyagent-studio CLI — launch the dashboard and apply or simulate blueprints from the terminal."
---

# Studio — CLI

Installing `pyagent-studio` adds the `pyagent` CLI — a `kubectl`-inspired interface for agent systems.

```bash
pip install pyagent-studio
pyagent --help
```

---

## apply — load and validate

Load a blueprint and print a summary.

```bash
pyagent apply customer-support.yaml
# ✓ Blueprint 'customer-support-system' v1.2.0 loaded and valid.
```

With issues:
```
Loaded 'customer-support-system' with 2 issue(s):
  [error] workflows.main.agents.routes.billing: Agent ref 'billing_agnt' not found.
  [warning] agents.legacy_agent: Agent defined but not referenced in any workflow.
```

Exit code `0` = valid, `1` = errors.

---

## get — list resources

```bash
pyagent get agents customer-support.yaml
#   classifier      Route to billing, technical, returns, or general
#   billing_agent   Handle billing disputes and subscription issues
#   technical_agent Handle technical and API issues
#   returns_agent   Handle returns and exchanges
#   formatter       Polish and format the final response

pyagent get workflows customer-support.yaml
#   main   (supervisor)

pyagent get providers customer-support.yaml
#   fast      anthropic / claude-haiku-3-5-20241022    max_tokens: 512
#   balanced  openai   / gpt-4o-mini                  max_tokens: 1024
#   expert    anthropic / claude-sonnet-4-20250514     max_tokens: 2048
```

---

## validate — static analysis

```bash
pyagent validate customer-support.yaml
# Valid

# Exit code 1 on errors — useful in CI
```

CI integration:
```yaml
# .github/workflows/blueprint-check.yml
- run: pyagent validate blueprints/production.yaml
```

---

## test — contract conformance

Run contract checks using MockLLM — no API costs.

```bash
pyagent test customer-support.yaml
# Testing 'customer-support-system'...
# All contract checks passed.
```

With failures:
```
Results: 1 error(s), 2 warning(s)
  [error] contracts.response_length: Output exceeded max_length 400 (got 612)
  [warning] contracts.no_pii: PII pattern check skipped (no output generated)
```

---

## simulate — dry run

Run a workflow against a task string. Uses MockLLM by default — no API costs.

```bash
# Mock simulation (default — free)
pyagent simulate customer-support.yaml main "I was charged twice this month"
# Running workflow 'main' in customer-support-system...
# [MockLLM] classifier → billing
# [MockLLM] billing_agent → "I understand your frustration..."
# [MockLLM] formatter → "Thank you for reaching out..."
# ✓ Completed in 0.012s (mock)

# Live run with real providers
pyagent simulate customer-support.yaml main "I need a refund" --live
# [claude-haiku] classifier → billing
# [claude-sonnet] billing_agent → "I'm sorry to hear about..."
# ✓ Completed in 1.8s, cost: $0.0042
```

---

## diff — semantic comparison

```bash
pyagent diff customer-support-v1.yaml customer-support-v2.yaml
# + providers.premium: {provider: anthropic, model: claude-opus-4-20250514}
# ~ agents.billing_agent.provider: expert → premium   [WARNING: model upgrade]
# ~ workflows.main.config.default_route: general → billing   [WARNING: routing change]
# - agents.legacy_agent   [INFO: removed]
```

Severity levels: `BREAKING`, `WARNING`, `INFO`.

---

## describe — full summary

```bash
pyagent describe customer-support.yaml
# Blueprint: customer-support-system v1.2.0
# Owner: platform-team  Tags: [support, production]
#
# Providers (3):
#   fast     anthropic / claude-haiku-3-5-20241022
#   balanced openai   / gpt-4o-mini
#   expert   anthropic / claude-sonnet-4-20250514
#
# Agents (5):   classifier, billing_agent, technical_agent, returns_agent, formatter
# Workflows (1): main (supervisor)
# Contracts (2): response_length, no_pii_in_response
```

---

## render — generate diagrams

```bash
# Mermaid diagram (default)
pyagent render customer-support.yaml

# Save to file
pyagent render customer-support.yaml -o docs/architecture.md

# Full Markdown documentation
pyagent render customer-support.yaml --format markdown -o docs/system.md
```

---

## providers — health monitoring

```bash
pyagent providers list
#   anthropic  claude-haiku-3-5-20241022      ✓ healthy  p50: 340ms
#   anthropic  claude-sonnet-4-20250514       ✓ healthy  p50: 1100ms
#   openai     gpt-4o-mini                    ✓ healthy  p50: 480ms

pyagent providers health
# All 3 providers healthy. Last checked: 2025-06-09T14:32:01Z
```

---

## dashboard — launch web UI

```bash
# Default port (8000)
pyagent dashboard

# Custom port
pyagent dashboard --port 3000

# Load a specific blueprint on startup
pyagent dashboard --blueprint customer-support.yaml

# Load recorded traces on startup
pyagent dashboard --trace traces/production_runs.jsonl

# Web UI available at http://localhost:8000
```

---

## Command Reference

```
pyagent apply      <file>                         Load and validate
pyagent get        agents|workflows|providers <file>
pyagent validate   <file>                         Static analysis
pyagent test       <file>                         Contract conformance
pyagent simulate   <file> <workflow> <task> [--live]
pyagent diff       <old> <new>                    Semantic diff
pyagent describe   <file>                         Full summary
pyagent render     <file> [--format mermaid|markdown] [-o <out>]
pyagent providers  list|health
pyagent dashboard  [--port N] [--blueprint <file>] [--trace <file>]
```

---

## See Also

- [Dashboard](dashboard.md) — the web UI
- [Blueprint CLI](../blueprint/cli.md) — `blueprint` command for spec-focused operations
