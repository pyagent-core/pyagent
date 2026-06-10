# pyagent-blueprint

**Declarative YAML specs for multi-agent LLM systems** — validate, compile, test, diff, render, and generate agent system blueprints.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](../../LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

## Install

```bash
pip install pyagent-blueprint
```

Depends on: `pyagent-patterns`, `pyagent-router`, `pyagent-providers`, `pyagent-context`, `pydantic`, `pyyaml`, `click`.

## Why Blueprints?

Without blueprints, agent systems are defined in code — hard to version, diff, review, or test without running them. With `pyagent-blueprint`, your agent system is a **YAML document** that is:
- **Versioned**: semantic version + git-diffable
- **Validated**: Pydantic schema + static analysis (dangling refs, security)
- **Compiled**: YAML → executable RuntimeGraph in one call
- **Testable**: contract conformance tests with MockLLM
- **Renderable**: Mermaid diagrams + Markdown docs auto-generated

## Blueprint YAML Schema

```yaml
api_version: pyagent/v1
metadata:
  name: customer-support
  version: 1.0.0
  description: Support routing system
  owner: platform-team

providers:
  primary:
    model: gpt-4.1-mini
  fallback:
    model: gpt-4.1-nano

context:
  memory:
    working_max_tokens: 128000
  compression:
    policy: semantic_lossless
    target_ratio: 0.6

agents:
  classifier:
    prompt: "Classify into: billing, tech, general"
    provider: primary
  billing:
    prompt: "Handle billing inquiries"
    provider: primary
    guardrails: [pii_redact]
  tech:
    prompt: "Handle technical support"
    provider: primary

workflows:
  support:
    pattern: supervisor
    agents:
      classifier: classifier
      routes:
        billing: billing
        tech: tech
    recovery:
      max_retries: 2
      timeout_seconds: 30

contracts:
  support:
    input:
      type: string
      max_tokens: 2000
    output:
      type: string
    sla:
      latency_p95_ms: 5000
      cost_max_usd: 0.05

observability:
  tracing:
    enabled: true
  cost_budget:
    daily_usd: 100.0
    alert_threshold: 0.8
```

## Loader — Load and Validate

```python
from pyagent_blueprint import load_blueprint, load_blueprint_from_str

# From file
spec = load_blueprint("blueprint.yaml")       # YAML or JSON
print(spec.metadata.name)                      # "customer-support"
print(spec.agents.keys())                      # dict_keys(['classifier', 'billing', 'tech'])

# From string
spec = load_blueprint_from_str(yaml_text)
```

## Compiler — Spec → RuntimeGraph

```python
import asyncio
from pyagent_blueprint import BlueprintCompiler, load_blueprint

spec = load_blueprint("blueprint.yaml")
compiler = BlueprintCompiler()
graph = compiler.compile(spec)

# Run a workflow
result = asyncio.run(graph.run("support", "I can't see my invoice"))
print(result.output)

# Inspect
print(graph.describe())
# {"metadata": {...}, "workflows": {"support": {"pattern_type": "Supervisor"}}}
```

## Validator — Static Analysis

```python
from pyagent_blueprint import BlueprintValidator, load_blueprint

spec = load_blueprint("blueprint.yaml")
validator = BlueprintValidator()
issues = validator.validate(spec)

for issue in issues:
    print(f"[{issue.severity}] {issue.path}: {issue.message}")
```

**Checks performed:**
- Dangling agent refs (workflow references undefined agent)
- Dangling provider refs (agent references undefined provider)
- Unknown pattern names (not in pattern registry)
- Contract → workflow ref mismatch
- Unrealistic SLA values
- Security: hardcoded API keys in prompts

## Renderer — Mermaid + Markdown

```python
from pyagent_blueprint import BlueprintRenderer, load_blueprint

spec = load_blueprint("blueprint.yaml")
renderer = BlueprintRenderer()

# Mermaid diagram
print(renderer.to_mermaid(spec))
# graph TD
#     classifier[Routes customer requests]
#     billing[Billing specialist]
#     tech[Technical support agent]
#     classifier -->|billing| billing
#     classifier -->|tech| tech

# Full Markdown documentation
md = renderer.to_markdown(spec)
```

## Differ — Semantic Diff

```python
from pyagent_blueprint import BlueprintDiffer, load_blueprint

old = load_blueprint("v1.yaml")
new = load_blueprint("v2.yaml")

differ = BlueprintDiffer()
changes = differ.diff(old, new)

print(differ.summary(changes))
# BREAKING (1):
#   [modified] workflows.support.pattern
# WARNING (2):
#   [modified] agents.billing.prompt
#   [removed] agents.legacy
```

Severity levels:
- **BREAKING**: pattern changes, API version changes
- **WARNING**: prompt changes, provider changes, removals
- **INFO**: metadata, descriptions, additions

## Tester — Contract Conformance

```python
import asyncio
from pyagent_blueprint import BlueprintTester, load_blueprint

spec = load_blueprint("blueprint.yaml")
tester = BlueprintTester()

results = asyncio.run(tester.test(spec))
print(tester.summary(results))
# Contract Tests: 1/1 passed
#   ✓ PASS  support
#          ✓ output_non_empty
#          ✓ output_is_string
#          ✓ input_within_token_limit
```

## Generator — Scaffold from Pattern

```python
from pyagent_blueprint import BlueprintGenerator

generator = BlueprintGenerator()
yaml_str = generator.generate(
    pattern="supervisor",
    agents=["classifier", "billing", "tech"],
    name="customer-support",
)
print(yaml_str)
```

## CLI Reference

```bash
# Validate
pyagent-blueprint validate blueprint.yaml

# Compile and inspect
pyagent-blueprint compile blueprint.yaml

# Render Mermaid diagram
pyagent-blueprint render blueprint.yaml
pyagent-blueprint render blueprint.yaml --format markdown -o docs.md

# Run contract tests
pyagent-blueprint test blueprint.yaml

# Semantic diff
pyagent-blueprint diff v1.yaml v2.yaml

# Generate scaffold
pyagent-blueprint generate --pattern supervisor --agents "classifier,billing,tech" --name my-system
```

## Integration

Blueprint uses all pyagent packages:
- **pyagent-patterns**: Pattern registry for workflow compilation (18 patterns)
- **pyagent-router**: CostEstimator, DifficultyScorer for routing strategies
- **pyagent-providers**: ProviderRegistry for real provider resolution
- **pyagent-context**: ContextConfigSpec drives memory + compression setup

## Full Documentation

See [pyagent.dev](https://pyagent.dev) for full API reference and integration guides.
