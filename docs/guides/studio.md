# Studio Guide

Terminal-based interactive workbench for designing, simulating, debugging, and governing agent systems.

## Overview

`pyagent-studio` provides a Textual TUI with 7 screens for working with blueprints interactively. It also exposes headless services for scripting and CI.

## Quick Start

```bash
pip install pyagent-studio[tui]
pyagent-studio blueprint.yaml
```

## Screens

| Screen | Purpose |
|--------|---------|
| **Dashboard** | List discovered blueprints, validation status |
| **Editor** | YAML editing with live validation panel |
| **Graph** | ASCII-rendered workflow DAG |
| **Simulation** | Run with MockLLM, stream results |
| **Traces** | Browse recorded trace spans |
| **Cost** | Cost breakdown tables and charts |
| **Governance** | Validation issues, compliance score, diff view |

## Key Bindings

| Key | Action |
|-----|--------|
| `Tab` / `Shift+Tab` | Switch screens |
| `q` | Quit |
| `Ctrl+S` | Save blueprint |
| `Ctrl+V` | Validate |
| `Ctrl+R` | Render graph |
| `Ctrl+T` | Run simulation |
| `Ctrl+D` | Show diff |

## Headless Services

Use the service layer without a TUI:

```python
from pyagent_studio import BlueprintService, SimulationService, GovernanceService

svc = BlueprintService()
spec = svc.load("blueprint.yaml")
issues = svc.validate()
graph = svc.compile()

sim = SimulationService()
result = await sim.run(spec, "support", "Help me")

gov = GovernanceService()
report = gov.check_compliance(spec)
print(gov.format_report(report))
```

### TraceService

```python
from pyagent_studio import TraceService

traces = TraceService()
spans = traces.load("traces.jsonl")
llm_calls = traces.query(event_type="llm_call")
print(traces.summary())
```

## API Reference

::: pyagent_studio
