---
description: "PyAgent Studio services — the aggregation layer behind the dashboard's runs, costs, and governance views."
---

# Studio — Python Services

Studio's web dashboard and CLI both call into a set of Python service classes. You can use these directly in your own code — the web layer is just a thin HTTP wrapper over them.

```python
from pyagent_studio.services.blueprint_service  import BlueprintService
from pyagent_studio.services.governance_service import GovernanceService
from pyagent_studio.services.simulation_service import SimulationService
from pyagent_studio.services.trace_service      import TraceService
from pyagent_studio.services.provider_service   import ProviderService
```

---

## BlueprintService

Load, validate, compile, and inspect blueprints.

```python
from pyagent_studio.services.blueprint_service import BlueprintService

svc = BlueprintService()

# Load from file
spec = svc.load("customer-support.yaml")

# Validate
issues = svc.validate()
print(f"Valid: {len(issues) == 0}")
for issue in issues:
    print(f"  [{issue.severity}] {issue.path}: {issue.message}")

# Compile to RuntimeGraph
graph = svc.compile()

# Summary dict
print(svc.summary())
# {
#   "loaded": true,
#   "name": "customer-support-system",
#   "version": "1.2.0",
#   "agents": 5,
#   "workflows": 1,
#   "providers": 3,
#   "contracts": 2
# }

# Discover all blueprints in a directory tree
paths = svc.discover_blueprints("./blueprints")
print(paths)  # ["./blueprints/production.yaml", "./blueprints/staging.yaml"]
```

---

## GovernanceService

Compliance scoring and semantic diff.

```python
from pyagent_studio.services.governance_service import GovernanceService
from pyagent_blueprint import load_blueprint

gov  = GovernanceService()
spec = load_blueprint("customer-support.yaml")

# Compliance report
report = gov.check_compliance(spec)
print(f"Score: {report.score:.0%}  ({report.passed}/{report.total_checks} checks)")
for issue in report.issues:
    print(f"  [{issue.severity}] {issue.path}: {issue.message}")

# Semantic diff
old_spec = load_blueprint("customer-support-v1.yaml")
new_spec = load_blueprint("customer-support-v2.yaml")

changes = gov.diff(old_spec, new_spec)
for c in changes:
    print(f"  [{c.severity}] {c.kind} {c.path}")

# Human-readable diff summary
print(gov.diff_summary(old_spec, new_spec))
# + providers.premium: {provider: anthropic, model: claude-opus-4-20250514}
# ~ agents.billing_agent.provider: expert → premium
# - agents.legacy_agent
```

### ComplianceReport fields

| Field | Type | Description |
|-------|------|-------------|
| `score` | float | 0.0–1.0, fraction of checks passed |
| `passed` | int | Number of passing checks |
| `total_checks` | int | Total checks run |
| `issues` | list | Failing checks with severity and path |

---

## SimulationService

Dry-run workflows with MockLLM — no API costs.

```python
import asyncio
from pyagent_studio.services.simulation_service import SimulationService
from pyagent_blueprint import load_blueprint

sim  = SimulationService()
spec = load_blueprint("customer-support.yaml")

result = asyncio.run(sim.run(spec, workflow="main", task="I need a refund"))

print(f"Success:  {result.success}")
print(f"Output:   {result.output}")
print(f"Duration: {result.elapsed_ms:.0f}ms")
print(f"Steps:    {len(result.steps)}")

if not result.success:
    print(f"Error: {result.error}")
```

### SimulationResult fields

| Field | Type | Description |
|-------|------|-------------|
| `success` | bool | Whether the run completed without error |
| `output` | str | Final output from the last agent |
| `elapsed_ms` | float | Total wall-clock duration |
| `steps` | list | Per-agent step records |
| `error` | str or None | Error message if `success=False` |

Each step in `result.steps`:
```python
step.agent_name    # "classifier"
step.output        # "[MockLLM] billing"
step.duration_ms   # 12.4
```

---

## TraceService

Load and query recorded `.jsonl` trace files produced by `pyagent-trace`.

```python
from pyagent_studio.services.trace_service import TraceService

svc   = TraceService()
spans = svc.load("traces/production_runs.jsonl")
print(f"Loaded {len(spans)} spans")

# Query by event type
llm_calls = svc.query(event_type="llm_call")

# Query by minimum duration
slow_spans = svc.query(min_duration_ms=2000)

# Inspect individual spans
for span in spans[:3]:
    print(f"[{span.event_type}] {span.agent_name}: "
          f"{span.duration_ms:.0f}ms, {span.tokens} tokens")
```

### Query parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `event_type` | str | Filter by event type (e.g. `"llm_call"`) |
| `agent_name` | str | Filter by agent name |
| `min_duration_ms` | float | Only spans longer than this |
| `max_duration_ms` | float | Only spans shorter than this |

---

## ProviderService

Health checks and cost monitoring for configured providers.

```python
from pyagent_studio.services.provider_service import ProviderService
from pyagent_blueprint import load_blueprint

svc  = ProviderService()
spec = load_blueprint("customer-support.yaml")

# List providers from spec
providers = svc.list_providers(spec)
for p in providers:
    print(f"{p.name}: {p.provider}/{p.model}")

# Health check all providers
health = svc.check_health()
for status in health:
    print(f"{status.model}: {'✓' if status.healthy else '✗'}  "
          f"p50={status.latency_p50_ms}ms  errors={status.error_count_1h}")

# Budget usage
budget = svc.get_budget_usage(spec)
for b in budget:
    print(f"{b.model}: ${b.used:.2f} / ${b.limit:.2f}  ({b.utilization:.0%})")
```

---

## Embedding Studio in a FastAPI App

The web layer is standard FastAPI — import the router and mount it inside your own app:

```python
from fastapi import FastAPI
from pyagent_studio.web.app import create_app

# Standalone Studio app
app = create_app()

# Or mount under a prefix in your own app
my_app = FastAPI()
studio  = create_app()
my_app.mount("/studio", studio)
```

---

## See Also

- [CLI](cli.md) — command-line access to the same services
- [Dashboard](dashboard.md) — web UI built on these services
- [Traces](traces.md) — trace file format and TraceService detail
- [API Reference](../../api/studio.md)
