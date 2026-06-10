# pyagent-studio

**The Kubernetes Dashboard for Agent Systems** — CLI + web control plane for designing, simulating, debugging, and governing multi-agent LLM blueprints.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](../../LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

## Install

```bash
pip install pyagent-studio
```

Depends on: `pyagent-blueprint`, `pyagent-trace`, `pyagent-providers`, `click`, `rich`, `litellm`, `fastapi`, `uvicorn`, `jinja2`.

## Quick Start

```bash
# Load and validate a blueprint
pyagent apply blueprint.yaml

# List agents
pyagent get agents blueprint.yaml

# Simulate a workflow (MockLLM, no API keys needed)
pyagent simulate blueprint.yaml support "Help me with billing"

# Simulate with real LLMs (set OPENAI_API_KEY, etc.)
pyagent simulate blueprint.yaml support "Help me with billing" --live

# Launch the web dashboard
pyagent dashboard
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `pyagent apply <file>` | Load, validate, and summarize a blueprint |
| `pyagent get <resource> <file>` | List agents, workflows, providers, or contracts |
| `pyagent validate <file>` | Run static validation checks |
| `pyagent test <file>` | Run contract conformance tests |
| `pyagent diff <old> <new>` | Semantic diff between two blueprints |
| `pyagent simulate <file> <wf> <task>` | Run a workflow with MockLLM or `--live` |
| `pyagent render <file>` | Render blueprint as Markdown or `--format mermaid` |
| `pyagent generate` | Scaffold a new blueprint YAML |
| `pyagent providers list` | List available LLM models (via LiteLLM) |
| `pyagent providers health` | Health-check LLM connectivity |
| `pyagent describe <file>` | Print full blueprint summary |
| `pyagent dashboard` | Launch web UI on http://localhost:8501 |

## Web Dashboard

Launch with `pyagent dashboard`. Built with **FastAPI + HTMX + Pico CSS** (zero JS build step).

| Page | URL | Description |
|------|-----|-------------|
| Overview | `/` | Blueprint summary, card grid, validation status |
| Agents | `/agents` | Agent table with prompts, providers, guardrails |
| Workflows | `/workflows` | Workflow table with Mermaid DAG diagrams |
| Simulate | `/simulate` | Run workflows with MockLLM or live LLMs |
| Traces | `/traces` | Live SSE trace stream + historical JSONL viewer |
| Governance | `/governance` | Compliance score, validation issues |
| Providers | `/providers` | LLM model list, health checks |
| Diff | `/diff` | Semantic diff between blueprint versions |
| Docs | `/docs` | Auto-rendered blueprint documentation |

## Provider Setup

pyagent-studio uses [LiteLLM](https://docs.litellm.ai/) for multi-provider LLM access. Set API keys via environment variables:

```bash
export OPENAI_API_KEY=sk-...
export ANTHROPIC_API_KEY=sk-ant-...
export GEMINI_API_KEY=...
```

No custom configuration needed — LiteLLM supports 100+ providers out of the box.

## Services (Headless API)

Use the services layer for scripting and CI:

```python
from pyagent_studio import BlueprintService, SimulationService, GovernanceService, ProviderService

# Load and validate
svc = BlueprintService()
spec = svc.load("blueprint.yaml")
issues = svc.validate()
print(svc.summary())

# Run simulation
import asyncio
sim = SimulationService()
result = asyncio.run(sim.run(spec, "support", "I can't see my invoice"))
print(result.output)

# Governance
gov = GovernanceService()
report = gov.check_compliance(spec)
print(gov.format_report(report))

# Provider health check
provider = ProviderService()
asyncio.run(provider.health_check())
```

## Comparison

| Feature | pyagent-studio | Langflow | CrewAI Studio | LangSmith |
|---------|---------------|----------|---------------|-----------|
| Declarative YAML blueprints | ✓ | ✗ (visual) | ✗ (Python) | ✗ |
| CLI control plane | ✓ | ✗ | ✗ | ✗ |
| Semantic diff / governance | ✓ | ✗ | ✗ | ✗ |
| MockLLM simulation | ✓ | ✗ | ✗ | ✗ |
| Multi-provider (100+) | ✓ (LiteLLM) | Limited | Limited | N/A |
| Portal-agnostic tracing | ✓ | ✗ | ✗ | Proprietary |
| Zero JS build step | ✓ (HTMX) | ✗ (React) | ✗ (React) | ✗ (React) |

## Full Documentation

See [pyagent.dev](https://pyagent.dev) for full API reference and integration guides.
