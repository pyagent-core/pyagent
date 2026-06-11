# Blueprint — Contracts & Observability

Contracts define input/output constraints and SLA requirements. The `BlueprintTester` runs contract checks against `MockLLM` before you ever hit production.

---

## ContractSpec

```yaml
contracts:
  response_length:
    type: max_length
    value: 400

  no_pii_in_response:
    type: regex_absent
    pattern: "\\b\\d{4}[- ]?\\d{4}[- ]?\\d{4}[- ]?\\d{4}\\b"

  contains_recommendation:
    type: regex_present
    pattern: "recommend|suggest|advise"

  valid_json_output:
    type: json_schema
    schema:
      type: object
      required: [recommendation, confidence]
```

### Contract Types

| Type | `value` / `pattern` | Passes when |
|------|---------------------|-------------|
| `max_length` | integer | Output length ≤ value characters |
| `min_length` | integer | Output length ≥ value characters |
| `regex_absent` | regex string | Pattern does NOT match output |
| `regex_present` | regex string | Pattern matches output |
| `json_schema` | JSON Schema object | Output is valid JSON matching schema |

---

## SLA Constraints

SLA constraints live inside contracts and express latency and cost requirements:

```yaml
contracts:
  support_response:
    type: max_length
    value: 400
    sla:
      latency_p95_ms: 5000      # 95th percentile latency budget
      cost_max_usd: 0.05        # Maximum per-call cost
      max_retries: 2
      timeout_seconds: 30.0
```

`BlueprintValidator` checks SLA values for sanity (negative latency, unrealistic timeouts) and will warn if `timeout_seconds` seems too low for the assigned provider tier.

---

## Running Contract Tests

Use `BlueprintTester` to run all contracts against `MockLLM` — no real API calls:

```python
import asyncio
from pyagent_blueprint import load_blueprint, BlueprintTester

spec   = load_blueprint("customer-support.yaml")
tester = BlueprintTester()

results = asyncio.run(tester.test(spec))
print(tester.summary(results))
# customer-support-system: all 2 contract checks passed.
```

From the CLI:
```bash
blueprint test customer-support.yaml
# Testing 'customer-support-system'...
# All contract checks passed.

# With failures:
# [error] contracts.response_length: Output exceeded max_length 400 (got 612)
```

---

## Observability

```yaml
observability:
  tracing:
    enabled: true
    record_to: traces/production_runs.jsonl   # Optional file sink
  cost_budget:
    daily_usd: 50.0    # Alert / hard-stop threshold
```

### Tracing

When `tracing.enabled: true`, the compiler attaches a `TraceRecorder` to all agents. Every LLM call emits a span with:

- `agent_name`, `workflow`, `pattern`
- `input_tokens`, `output_tokens`, `duration_ms`
- `provider`, `model`, `cost_estimate`

If `record_to` is set, spans are also written to a JSONL file — which Studio's trace explorer can load.

```yaml
observability:
  tracing:
    enabled: true
    record_to: traces/runs.jsonl
```

### Cost Budget

```yaml
observability:
  cost_budget:
    daily_usd: 50.0
```

The compiler wires a `CostBudget` guard that accumulates cost across calls. When the daily limit is reached, further calls raise `BudgetExceededError` from `pyagent-compress`. Studio's `/providers` dashboard shows budget utilisation in real time.

---

## Validation Checks Summary

The `BlueprintValidator` runs 6 categories of checks across the full spec:

| Check | What it catches |
|-------|----------------|
| Agent refs | Workflow references a non-existent agent name |
| Provider refs | Agent or workflow references an undefined provider |
| Pattern names | Unknown pattern key (typo in `pattern:` field) |
| Contract refs | Workflow references an undefined contract |
| SLA values | Negative latency, `timeout_seconds < 0`, unrealistic retries |
| Security | Hardcoded API keys found in prompt strings |

```python
from pyagent_blueprint import load_blueprint
from pyagent_blueprint.validator import BlueprintValidator, IssueSeverity

spec     = load_blueprint("blueprint.yaml")
issues   = BlueprintValidator().validate(spec)

errors   = [i for i in issues if i.severity == IssueSeverity.ERROR]
warnings = [i for i in issues if i.severity == IssueSeverity.WARNING]

if errors:
    for e in errors:
        print(f"[error] {e.path}: {e.message}")
    raise SystemExit(1)
```

---

## See Also

- [CLI](cli.md) — `blueprint test`, `blueprint validate`
- [Python API](compiler.md) — `BlueprintTester`, `BlueprintValidator`
- [Observability Guide](../../guides/studio.md) — Studio trace explorer
- [Full Spec Reference](spec-format.md)
