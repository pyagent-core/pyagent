# pyagent-studio

**The Kubernetes Dashboard for Agent Systems** — a `kubectl`-inspired CLI and web control plane for designing, simulating, debugging, and governing multi-agent blueprints.

Studio is to pyagent what `kubectl` + the Kubernetes Dashboard are to Kubernetes: a single pane of glass for your entire agent infrastructure.

```bash
pip install pyagent-studio
```

---

## What Studio Gives You

| Capability | Where |
|------------|-------|
| Load and validate blueprints | `pyagent apply` + Studio `/governance` |
| Inspect agents, providers, workflows | `pyagent get` + Studio `/agents` `/workflows` |
| Simulate workflows without API costs | `pyagent simulate` + Studio `/simulate` |
| Diff blueprint versions | `pyagent diff` + Studio `/diff` |
| Explore recorded traces | `pyagent dashboard` + Studio `/traces` |
| Monitor provider health and cost | `pyagent providers` + Studio `/providers` |

---

## Architecture

```mermaid
flowchart TD
    BP[blueprint.yaml] --> CLI[pyagent CLI\nkubectl-style commands]
    CLI --> BS[BlueprintService]
    CLI --> GS[GovernanceService]
    CLI --> SIM[SimulationService]
    CLI --> PS[ProviderService]

    BP --> WEB[Web Dashboard\nlocalhost:8000]
    WEB --> OV[/overview]
    WEB --> WF[/workflows]
    WEB --> AGT[/agents]
    WEB --> TR[/traces]
    WEB --> SIL[/simulate]
    WEB --> GOV[/governance]
    WEB --> PRV[/providers]
    WEB --> DIFF[/diff]
    WEB --> DOCS[/docs]

    TR --> TS[TraceService\nload .jsonl files]
```

---

## Quick Start

```bash
# 1. Load a blueprint
pyagent apply customer-support.yaml

# 2. Validate it
pyagent validate customer-support.yaml

# 3. Simulate a workflow (no API costs)
pyagent simulate customer-support.yaml main "I was charged twice"

# 4. Launch the web dashboard
pyagent dashboard
# → http://localhost:8000
```

---

## Sub-pages

- [CLI](cli.md) — all `pyagent` commands
- [Dashboard](dashboard.md) — the 9 web UI sections
- [Services](services.md) — Python services API
- [Traces](traces.md) — loading, querying, and viewing trace files

---

## See Also

- [Blueprint Package](../blueprint/index.md) — the YAML spec Studio loads and compiles
- [Blueprint Guide](../../guides/blueprint.md) — narrative walkthrough
- [Studio Guide](../../guides/studio.md) — guide-level walkthrough
- [API Reference](../../api/studio.md)
