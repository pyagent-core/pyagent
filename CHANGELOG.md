# Changelog

All notable changes to the PyAgent packages are documented here.

### Released versions
## [0.3.0] – 2026-08-08
## [0.2.4] – 2026-06-19
## [0.2.0] – 2026-06-08
## [0.1.0] – 2026-06-07

## [0.3.0] – 2026-08-08

### Added
- `pyagent-blueprint` — pluggable `RuntimeAdapter` framework: a blueprint now compiles onto any
  conforming adapter, not just the native `pyagent` pattern registry. Ships with a zero-dependency
  reference implementation (`single_agent`, `sequential_chain`, `state_machine`, `simple_loop`)
  usable with no extra installs.
- Four new adapter packages, each independently installable and each certified against the same
  `RuntimeAdapter` conformance suite:
  - `pyagent-blueprint-adapter-langgraph` — targets LangGraph `StateGraph`
  - `pyagent-blueprint-adapter-crewai` — targets CrewAI `Crew`
  - `pyagent-blueprint-adapter-openai-agents` — targets the OpenAI Agents SDK
  - `pyagent-blueprint-adapter-semantic-kernel` — targets Microsoft Semantic Kernel

### Changed
- `pyagent-blueprint`: the `pyagent-patterns`/`pyagent-router`/`pyagent-providers`/`pyagent-context`
  dependency chain moved from required to an optional `pyagent` extra
  (`pip install "pyagent-blueprint[pyagent]"`) — installing `pyagent-blueprint` alone now only pulls
  in the zero-dependency reference adapters.
- `pyagent-blueprint` CLI: `simulate` renamed to `test` (`pyagent-blueprint test blueprint.yaml`) to
  reflect that it runs contract-conformance checks against a `MockLLM`, not a live simulation.
- Fixed blueprint compiler bugs surfaced while re-wiring all 34 example blueprints against the new
  adapter framework.

## [0.2.4] – 2026-06-19

### Added
- `pyagent-studio` — `kubectl`-style CLI + FastAPI web dashboard (simulate, diff, trace explorer,
  governance).
- `robots.txt`, Open Graph/Twitter cards, JSON-LD, and SEO-focused homepage copy.

## [0.2.0] – 2026-06-08
## [0.1.0] – 2026-06-07

### Added
- `pyagent-patterns` – 18 composable multi-agent orchestration patterns (supervisor, pipeline, fan-out/fan-in, hierarchical, orchestrator-workers, self-reflection, cross-reflection, debate, voting, evaluator-optimizer, role-based, layered, topology, blackboard, talker-reasoner, swarm, human-in-the-loop, ReAct)
- `pyagent-compress` – inter-agent message compression and token budget management
- `pyagent-router` – difficulty-aware routing and model selection
- `pyagent-trace` – pattern-aware OpenTelemetry tracing
- `pyagent-all` – meta-package installing all of the above
