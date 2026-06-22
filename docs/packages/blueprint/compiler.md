---
description: "The BlueprintCompiler Python API — compile a blueprint spec into a runnable RuntimeGraph."
---

# Blueprint — Python API

The `pyagent_blueprint` package exposes seven classes covering the full lifecycle: load → validate → compile → run → test → diff → render.

---

## Loading

```python
from pyagent_blueprint import load_blueprint, load_blueprint_from_str

spec = load_blueprint("customer-support.yaml")         # From file
spec = load_blueprint_from_str(yaml_string)            # From string
```

The `BlueprintSpec` object is a Pydantic model — all fields are type-checked at load time.

```python
print(spec.metadata.name)       # "customer-support-system"
print(spec.metadata.version)    # "1.2.0"
print(list(spec.providers))     # ["fast", "balanced", "expert"]
print(list(spec.agents))        # ["classifier", "billing_agent", ...]
print(list(spec.workflows))     # ["main"]
```

---

## BlueprintValidator

Static analysis — run before compiling or deploying.

```python
from pyagent_blueprint.validator import BlueprintValidator, IssueSeverity

validator = BlueprintValidator()
issues    = validator.validate(spec)

errors   = [i for i in issues if i.severity == IssueSeverity.ERROR]
warnings = [i for i in issues if i.severity == IssueSeverity.WARNING]
infos    = [i for i in issues if i.severity == IssueSeverity.INFO]

for issue in errors:
    print(f"[{issue.severity}] {issue.path}: {issue.message}")

if errors:
    raise SystemExit(1)
```

Each `ValidationIssue` has:

| Attribute | Type | Description |
|-----------|------|-------------|
| `severity` | `IssueSeverity` | `ERROR`, `WARNING`, or `INFO` |
| `path` | string | Dotted path to the offending field (e.g. `workflows.main.agents.routes.billing`) |
| `message` | string | Human-readable explanation |

---

## BlueprintCompiler

Transform a validated spec into a runnable `RuntimeGraph`.

```python
import asyncio
from pyagent_blueprint import load_blueprint, BlueprintCompiler
from pyagent_providers import ProviderRegistry, AnthropicLLM, OpenAILLM

registry = ProviderRegistry()
registry.register("anthropic", AnthropicLLM)
registry.register("openai",    OpenAILLM)

spec   = load_blueprint("customer-support.yaml")
graph  = BlueprintCompiler(provider_registry=registry).compile(spec)

result = asyncio.run(graph.run("main", "I was charged twice this month"))
print(result.output)
print(f"Route: {result.metadata.get('route_key')}")
print(f"Cost:  ${result.cost_estimate:.4f}")
```

### Compile without real providers (MockLLM)

```python
graph = BlueprintCompiler().compile(spec)   # No provider_registry — uses MockLLM
```

### Inspect the compiled graph

```python
import json
print(json.dumps(graph.describe(), indent=2))
# {
#   "workflows": {
#     "main": { "pattern": "supervisor", "agents": [...], "config": {...} }
#   },
#   "metadata": { "name": "customer-support-system", "version": "1.2.0" }
# }
```

### Wire shared context

```python
from pyagent_context import ContextLedger, ContextItem, TrustLevel

ledger = ContextLedger()
ledger.append(ContextItem(
    content="Customer account created 2024-01-15",
    source="database",
    trust=TrustLevel.VERIFIED,
))

graph.wire_context(ledger)   # Sets ledger on ALL agents
result = asyncio.run(graph.run("main", "When was my account created?"))
```

---

## BlueprintRenderer

Generate Mermaid diagrams or Markdown documentation programmatically.

```python
from pyagent_blueprint import BlueprintRenderer

renderer = BlueprintRenderer()

# Mermaid flowchart
mermaid_str = renderer.to_mermaid(spec)
print(mermaid_str)

# Full Markdown documentation
markdown_str = renderer.to_markdown(spec)
with open("docs/system.md", "w") as f:
    f.write(markdown_str)
```

---

## BlueprintDiffer

Semantic diff between two spec versions — compare prompts, providers, agent wiring, and config.

```python
from pyagent_blueprint import load_blueprint, BlueprintDiffer

old_spec = load_blueprint("customer-support-v1.yaml")
new_spec = load_blueprint("customer-support-v2.yaml")

differ  = BlueprintDiffer()
changes = differ.diff(old_spec, new_spec)

print(differ.summary(changes))
# + providers.premium: {provider: anthropic, model: claude-opus-4-20250514}
# ~ agents.billing_agent.provider: expert → premium  [WARNING]
# - agents.legacy_agent  [INFO]
```

Each `Change` has `kind` (ADD, MODIFY, REMOVE), `path`, `old_value`, `new_value`, and `severity` (BREAKING, WARNING, INFO).

---

## BlueprintTester

Run contract conformance checks with MockLLM — no API costs, great for CI.

```python
import asyncio
from pyagent_blueprint import load_blueprint, BlueprintTester

spec    = load_blueprint("customer-support.yaml")
tester  = BlueprintTester()

results = asyncio.run(tester.test(spec))
print(tester.summary(results))
# customer-support-system: all 2 contract checks passed.
```

Each result in `results` has `contract_name`, `passed`, `message`, and `severity`.

---

## BlueprintGenerator

Scaffold a new blueprint YAML from a pattern name and agent list.

```python
from pyagent_blueprint import BlueprintGenerator

gen = BlueprintGenerator()

yaml_str = gen.generate(
    pattern="supervisor",
    agents=["classifier", "billing", "technical", "general"],
)
print(yaml_str)
# api_version: pyagent/v1
# metadata:
#   name: generated-supervisor
#   version: "1.0.0"
# agents:
#   classifier: { prompt: "" }
#   billing:    { prompt: "" }
# ...
```

---

## RuntimeGraph

The compiled result of `BlueprintCompiler.compile()`. Its main methods:

| Method | Description |
|--------|-------------|
| `run(workflow, task)` | Execute a named workflow with a task string |
| `describe()` | Return a dict describing all compiled workflows |
| `wire_context(ledger)` | Set a shared `ContextLedger` on all agents |

```python
graph = BlueprintCompiler().compile(spec)

# Run a workflow
result = asyncio.run(graph.run("main", task_string))

# Result fields
print(result.output)            # Final text output
print(result.cost_estimate)     # Estimated cost in USD
print(result.metadata)          # Pattern-specific metadata (route_key, rounds, etc.)
```

---

## See Also

- [CLI](cli.md) — command-line interface for the same operations
- [Spec Format](spec-format.md) — full YAML reference
- [API Reference](../../api/blueprint.md)
