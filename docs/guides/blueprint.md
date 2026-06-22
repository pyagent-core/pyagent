---
description: "Guide to PyAgent blueprints — declare agents, workflows, providers, and contracts in typed YAML and compile them into a runnable graph."
---

# Blueprint Guide

Declarative YAML specs for multi-agent LLM systems — validate, compile, test, diff, render, and generate.

## Overview

`pyagent-blueprint` lets you define your entire agent system as a versioned YAML document. The blueprint is validated against a Pydantic schema, compiled into an executable `RuntimeGraph`, and can be tested, diffed, and rendered without writing code.

## Blueprint YAML Schema

```yaml
api_version: pyagent/v1
metadata:
  name: customer-support
  version: 1.0.0
  description: Support routing system

providers:
  primary:
    model: gpt-4.1-mini

agents:
  classifier:
    prompt: "Classify into: billing, tech, general"
    provider: primary
  billing:
    prompt: "Handle billing inquiries"
    provider: primary

workflows:
  support:
    pattern: supervisor
    agents:
      classifier: classifier
      routes:
        billing: billing

contracts:
  support:
    input: { type: string, max_tokens: 2000 }
    output: { type: string }
    sla:
      latency_p95_ms: 5000
      cost_max_usd: 0.05

observability:
  tracing: { enabled: true }
  cost_budget: { daily_usd: 100.0 }
```

## Loading

```python
from pyagent_blueprint import load_blueprint, load_blueprint_from_str

spec = load_blueprint("blueprint.yaml")       # File
spec = load_blueprint_from_str(yaml_string)    # String
```

## Compilation

Transform YAML into a runnable graph:

```python
from pyagent_blueprint import BlueprintCompiler

compiler = BlueprintCompiler()
graph = compiler.compile(spec)
result = await graph.run("support", "I can't see my invoice")
```

## Validation

Static analysis catches issues before runtime:

```python
from pyagent_blueprint import BlueprintValidator

validator = BlueprintValidator()
issues = validator.validate(spec)
```

**Checks performed:**

- Dangling agent references
- Dangling provider references
- Unknown pattern names
- Contract → workflow mismatches
- Unrealistic SLA values
- Hardcoded API keys in prompts

## Rendering

Generate documentation automatically:

```python
from pyagent_blueprint import BlueprintRenderer

renderer = BlueprintRenderer()
mermaid = renderer.to_mermaid(spec)    # Mermaid flowchart
markdown = renderer.to_markdown(spec)  # Full Markdown doc
```

## Diffing

Semantic diff between blueprint versions:

```python
from pyagent_blueprint import BlueprintDiffer

differ = BlueprintDiffer()
changes = differ.diff(old_spec, new_spec)
print(differ.summary(changes))
```

Severity levels: **BREAKING** (pattern/API changes), **WARNING** (prompt/provider changes), **INFO** (metadata).

## Contract Testing

Test blueprints with MockLLM:

```python
from pyagent_blueprint import BlueprintTester

tester = BlueprintTester()
results = await tester.test(spec)
print(tester.summary(results))
```

## Scaffolding

Generate a blueprint from a pattern name:

```python
from pyagent_blueprint import BlueprintGenerator

gen = BlueprintGenerator()
yaml_str = gen.generate(
    pattern="supervisor",
    agents=["classifier", "billing", "tech"],
)
```

## CLI

```bash
pyagent-blueprint validate blueprint.yaml
pyagent-blueprint compile blueprint.yaml
pyagent-blueprint render blueprint.yaml --format markdown
pyagent-blueprint test blueprint.yaml
pyagent-blueprint diff v1.yaml v2.yaml
pyagent-blueprint generate --pattern supervisor --agents "a,b,c"
```

## API Reference

→ See the full [Blueprint API Reference](../api/blueprint.md).
