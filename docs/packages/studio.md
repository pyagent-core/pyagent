# pyagent-studio

**The Kubernetes Dashboard for Agent Systems** — CLI workbench and web control plane for designing, simulating, debugging, and governing multi-agent LLM blueprints.

Studio is to pyagent what `kubectl` + the Kubernetes Dashboard are to Kubernetes: a single pane of glass for your entire agent infrastructure.

```bash
pip install pyagent-studio
```

---

## Architecture

```mermaid
flowchart TD
    BP[blueprint.yaml] --> CLI[pyagent CLI\nkubectl-style commands]
    CLI --> BS[BlueprintService\nload / validate / compile]
    CLI --> GS[GovernanceService\ncompliance + diff]
    CLI --> SIM[SimulationService\nMockLLM dry runs]
    CLI --> PS[ProviderService\nhealth + cost]

    BP --> WEB[Web Dashboard\nlocalhost:8000]
    WEB --> OV[/overview\nblueprint summary]
    WEB --> WF[/workflows\npattern diagrams]
    WEB --> AGT[/agents\nprompt viewer]
    WEB --> TR[/traces\ntrace explorer]
    WEB --> SIL[/simulate\ninteractive runner]
    WEB --> GOV[/governance\ncompliance scores]
    WEB --> PRV[/providers\nhealth + latency]

    TR --> TS[TraceService\nload .jsonl files]
```

---

## CLI — `pyagent` Command

Studio installs the `pyagent` CLI — a `kubectl`-inspired interface for agent systems.

### apply — load and validate

```bash
pyagent apply customer-support.yaml
# ✓ Blueprint 'customer-support-system' v1.2.0 loaded and valid.

# With issues:
# Loaded 'customer-support-system' with 2 issue(s):
#   [error] workflows.main.agents.routes.billing: Agent ref 'billing_agnt' not found.
#   [warning] agents.legacy_agent: Agent defined but not referenced in any workflow.
```

### get — list resources

```bash
pyagent get agents customer-support.yaml
#   classifier      (Route to billing, technical, returns, or general)
#   billing_agent   (Handle billing disputes and subscription issues)
#   technical_agent (Handle technical and API issues)
#   returns_agent   (Handle returns and exchanges)
#   formatter       (Polish and format the final response)

pyagent get workflows customer-support.yaml
#   main

pyagent get providers customer-support.yaml
#   fast      (claude-haiku-3-5-20241022)
#   balanced  (gpt-4o-mini)
#   expert    (claude-sonnet-4-20250514)
```

### validate — static analysis

```bash
pyagent validate customer-support.yaml
# Valid

# Exit code 1 on errors — great for CI pipelines
# Add to GitHub Actions:
# - run: pyagent validate blueprints/production.yaml
```

### test — contract conformance

```bash
pyagent test customer-support.yaml
# Testing 'customer-support-system'...
# All contract checks passed.

# With failures:
# Results: 1 error(s), 2 warning(s)
#   [error] contracts.response_length: Output exceeded max_length 400
#   [warning] contracts.no_pii: PII pattern check skipped (no output generated)
```

### simulate — dry run with MockLLM (no API costs)

```bash
# Basic simulation
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

### diff — semantic comparison

```bash
pyagent diff customer-support-v1.yaml customer-support-v2.yaml
# + providers.premium: {provider: anthropic, model: claude-opus-4-20250514}
# ~ agents.billing_agent.provider: expert → premium  (model upgrade)
# ~ workflows.main.config.default_route: general → billing  (routing change)
# - agents.legacy_agent  (removed)
```

### describe — full blueprint summary

```bash
pyagent describe customer-support.yaml
# Blueprint: customer-support-system v1.2.0
# Owner: platform-team  Tags: [support, production]
#
# Providers (3):
#   fast     anthropic/claude-haiku-3-5-20241022
#   balanced openai/gpt-4o-mini
#   expert   anthropic/claude-sonnet-4-20250514
#
# Agents (5):  classifier, billing_agent, technical_agent, returns_agent, formatter
# Workflows (1): main (supervisor)
# Contracts (2): response_length, no_pii_in_response
```

### render — generate diagrams

```bash
# Mermaid architecture diagram
pyagent render customer-support.yaml
pyagent render customer-support.yaml -o docs/architecture.md

# Full markdown documentation
pyagent render customer-support.yaml --format markdown -o docs/system-doc.md
```

### providers — health and cost monitoring

```bash
pyagent providers list
#   anthropic  claude-haiku-3-5-20241022    ✓ healthy  p50: 340ms
#   anthropic  claude-sonnet-4-20250514     ✓ healthy  p50: 1100ms
#   openai     gpt-4o-mini                  ✓ healthy  p50: 480ms

pyagent providers health
# All 3 providers healthy. Last checked: 2025-06-09T14:32:01Z
```

### dashboard — launch web UI

```bash
# Launch on default port
pyagent dashboard

# Custom port and blueprint
pyagent dashboard --port 3000 --blueprint customer-support.yaml

# With recorded traces loaded
pyagent dashboard --trace traces/production_runs.jsonl
# Web UI available at http://localhost:8000
```

---

## Web Dashboard

The dashboard exposes every Studio capability through a browser UI — designed for the team members who don't live in a terminal.

### /overview — Blueprint Summary

- Metadata card: name, version, owner, tags
- Resource counts: agents, workflows, providers, contracts
- Compliance score (0–100%) from GovernanceService
- Quick-action buttons: validate, simulate, view traces

### /workflows — Pattern Diagrams

- Interactive Mermaid diagram for each workflow
- Click any agent node → see its prompt and provider
- Pattern type badge: supervisor, pipeline, fan-out, etc.
- "Run simulation" button in-page

### /agents — Prompt Viewer

- Full system prompt for each agent
- Provider and model info
- Tools and guardrails assigned
- Edit prompt → auto-revalidates in real time

### /simulate — Interactive Runner

```
Workflow: [main ▼]
Input:    [I was charged twice this month          ]  [Run Mock] [Run Live]

──────────────────────────────────────────────────
[classifier → billing]  0.012s  MockLLM
[billing_agent]         0.024s  MockLLM
  Output: "I understand your frustration. Let me look into the double charge..."
[formatter]             0.008s  MockLLM
──────────────────────────────────────────────────
Final: "I understand your frustration. Let me look into..."
Cost: $0.00 (mock)  |  Duration: 0.044s
```

### /traces — Trace Explorer

Visualise recorded `.jsonl` trace files (from `pyagent-trace` Recorder):

```
traces/production_runs.jsonl  →  loaded 1,240 spans from 180 runs

Run #174  pipeline  3.4s  $0.0092
├── extractor    0.9s  claude-haiku  180→42 tok   $0.00006
├── fact_checker 1.8s  gpt-4o-mini   60→85 tok   $0.00009
└── writer       0.7s  claude-sonnet 145→220 tok  $0.00840

Cost by model (last 7 days):
  claude-sonnet-4-20250514 ████████████████  $24.80 (72%)
  gpt-4o-mini              ████              $6.20  (18%)
  claude-haiku-3-5-20241022 ██               $3.40  (10%)
```

### /governance — Compliance Scores

```
Blueprint: customer-support-system v1.2.0
Compliance Score: 83%  (5/6 checks passed)

✓ Agent refs       All workflow agent references resolve
✓ Provider refs    All agent provider references resolve
✓ Pattern names    All patterns are registered
✓ Contract refs    All contract references resolve
✗ SLA values       timeout_seconds: 30s may be too low for expert provider
✓ Security         No hardcoded API keys detected

Diff vs v1.1.0:
  ~ agents.billing_agent.provider: expert → premium  (model upgrade, +$0.008/call)
```

### /providers — Health Dashboard

```
Provider Health (last 5 minutes)

anthropic / claude-haiku-3-5-20241022
  Status: ✓ HEALTHY   Avg latency: 340ms   p99: 820ms
  Errors (1h): 0   Budget used: $1.24 / $50.00

anthropic / claude-sonnet-4-20250514
  Status: ✓ HEALTHY   Avg latency: 1,100ms   p99: 2,400ms
  Errors (1h): 2 (rate limit)   Budget used: $18.60 / $50.00

openai / gpt-4o-mini
  Status: ✓ HEALTHY   Avg latency: 480ms   p99: 1,100ms
  Errors (1h): 0   Budget used: $4.30 / $50.00
```

---

## Python Services API

Studio's services are usable directly in Python — Studio's web layer just calls them.

### BlueprintService

```python
from pyagent_studio.services.blueprint_service import BlueprintService

svc = BlueprintService()
spec = svc.load("customer-support.yaml")

issues = svc.validate()
print(f"Valid: {len(issues) == 0}")

graph = svc.compile()
print(svc.summary())
# {"loaded": True, "name": "customer-support-system", "version": "1.2.0",
#  "agents": 5, "workflows": 1, "providers": 3, "contracts": 2}

# Discover all blueprints in a directory
paths = svc.discover_blueprints("./blueprints")
```

### GovernanceService

```python
from pyagent_studio.services.governance_service import GovernanceService
from pyagent_blueprint import load_blueprint

gov = GovernanceService()
spec = load_blueprint("customer-support.yaml")

report = gov.check_compliance(spec)
print(f"Compliance: {report.score:.0%} ({report.passed}/{report.total_checks} checks)")
for issue in report.issues:
    print(f"  [{issue.severity}] {issue.path}: {issue.message}")

# Semantic diff for change review
old_spec = load_blueprint("customer-support-v1.yaml")
new_spec = load_blueprint("customer-support-v2.yaml")
changes = gov.diff(old_spec, new_spec)
print(gov.diff_summary(old_spec, new_spec))
```

### SimulationService

```python
import asyncio
from pyagent_studio.services.simulation_service import SimulationService
from pyagent_blueprint import load_blueprint

sim = SimulationService()
spec = load_blueprint("customer-support.yaml")

result = asyncio.run(sim.run(spec, workflow="main", task="I need a refund"))
print(f"Success: {result.success}")
print(f"Output: {result.output}")
print(f"Duration: {result.elapsed_ms:.0f}ms")
if not result.success:
    print(f"Error: {result.error}")
```

### TraceService

```python
from pyagent_studio.services.trace_service import TraceService

svc = TraceService()
spans = svc.load("traces/production_runs.jsonl")

print(f"Loaded {len(spans)} spans")

# Query
llm_calls = svc.query(event_type="llm_call")
slow_spans = svc.query(min_duration_ms=2000)

for span in spans[:5]:
    print(f"[{span.event_type}] {span.agent_name}: {span.duration_ms:.0f}ms, {span.tokens} tokens")
```

---

## CI/CD Integration

```yaml
# .github/workflows/blueprint-check.yml
name: Blueprint CI

on: [push, pull_request]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install pyagent-studio
      - name: Validate all blueprints
        run: |
          for f in blueprints/*.yaml; do
            echo "Validating $f..."
            pyagent validate "$f"
          done

  diff:
    runs-on: ubuntu-latest
    if: github.event_name == 'pull_request'
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 0 }
      - run: pip install pyagent-studio
      - name: Show blueprint diff
        run: |
          git show HEAD~1:blueprints/production.yaml > /tmp/old.yaml || true
          pyagent diff /tmp/old.yaml blueprints/production.yaml || true
```

---

## See Also

- [Blueprint Package](blueprint.md) — YAML spec format and Python compiler API
- [Trace Package](trace.md) — recording traces that Studio's trace viewer loads
- [Providers Package](providers.md) — provider health data shown in Studio's /providers
- [API Reference](../api/studio.md)
