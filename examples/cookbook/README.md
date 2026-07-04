# PyAgent Cookbook — Production Examples

Each recipe in this folder is a self-contained **mini-project** that mirrors a real production microservice:

```
<domain>/<recipe>/
  __init__.py        package marker
  blueprint.yaml     declarative system spec (providers, agents, workflows, observability)
  agents.py          agent factory — system prompts copied verbatim from the docs recipe
  models.py          Pydantic request/response models + output parsers
  pipeline.py        orchestration wiring, BoundedExecution, CLI demo with trace + cost output
  api.py             FastAPI server with per-request TraceEventBus + JsonlExporter
  tests/
    conftest.py      recipe-scoped pytest fixtures
    test_<recipe>.py MockLLM tests — no real LLM calls needed
```

## Setup

```bash
git clone https://github.com/pyagent-core/pyagent
cd pyagent/examples/cookbook

pip install pyagent-all fastapi uvicorn[standard] httpx tenacity pydantic python-dotenv pytest pytest-asyncio

cp .env.example .env
# edit .env and fill in the keys you need
```

## Run the CLI demo

```bash
python -m finance-trading.aml_monitoring.pipeline
```

## Run the FastAPI server

```bash
uvicorn finance-trading.aml_monitoring.api:app --reload
# POST http://localhost:8000/monitor
```

## Run tests (no API keys needed)

```bash
pytest finance-trading/aml_monitoring/tests/ -v
# or all recipes at once:
pytest . -q
```

## Recipes

| Domain | Recipe | Pattern | Complexity |
|--------|--------|---------|------------|
| Finance & Trading | aml_monitoring | Pipeline + HITL | Advanced |
| Finance & Trading | trading_signals | Fan-Out / Fan-In | Advanced |
| Finance & Trading | wealth_rebalancing | Pipeline | Intermediate |
| Finance & Trading | earnings_call | Self-Reflection | Intermediate |
| Finance & Trading | esg_analyzer | Orchestrator-Workers | Advanced |
| Finance & Trading | robo_advisor | Role-Based | Intermediate |
| Finance & Trading | loan_underwriting | Debate | Advanced |
| Finance & Trading | loan_origination | Topology | Advanced |
| Finance & Trading | portfolio_review | Evaluator-Optimizer | Advanced |
