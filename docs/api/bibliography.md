---
description: "PyAgent API & hooks bibliography — every public class, method, hook, and protocol across all pyagent-* packages, verified against the real source."
---

# API & Hooks Bibliography

**An at-a-glance map of every public class, method, hook, and protocol across all pyagent-\* packages.**

This is the companion overview to the per-package API Reference pages in this section — use it as a
quick-lookup cheat sheet, then open a package page (e.g. [pyagent-patterns](patterns/base.md),
[pyagent-trace](trace.md)) for the full generated signatures and docstrings, or follow a **source**
link below to read the real file. It also collects cross-cutting references you won't find on a
single package page: the [Hook Event Reference](#hook-event-reference) and the
[Cross-Package Integration Matrix](#cross-package-integration-matrix).

Every row on this page is checked against the real `packages/*/src/` source, not hand-maintained
from memory — if this page and the source ever disagree, the source wins and this page has drifted.

<div id="bib-filter-bar">
  <input id="bib-filter" type="text" placeholder="Filter by class, method, or enum name…" autocomplete="off">
  <div id="bib-filter-count"></div>
</div>

<div id="bib-content" markdown>

<div class="bib-section" markdown>

## pyagent-blueprint
<span class="bib-source">[source ↗](https://github.com/pyagent-core/pyagent/blob/main/packages/pyagent-blueprint/src/pyagent_blueprint/)</span>

Declarative YAML specs — validate, compile, test, diff, render, scaffold, and package. Compiles onto
five real runtime engines via the [adapter layer](#runtime-adapters) — see [Adapters](adapters.md)
for the full comparison table and code.

### Core Classes

| Class | Constructor | Key Methods |
|-------|-------------|-------------|
| `BlueprintValidator` | `BlueprintValidator()` | `.validate(spec) → list[ValidationIssue]` |
| `BlueprintRenderer` | `BlueprintRenderer()` | `.to_mermaid(spec)`, `.to_markdown(spec)` |
| `BlueprintDiffer` | `BlueprintDiffer()` | `.diff(old, new) → list[Change]`, `.summary(changes)` |
| `BlueprintTester` | `BlueprintTester()` | `.test(spec) → list[TestResult]`, `.summary(results)` |
| `BlueprintGenerator` | `BlueprintGenerator()` | `.generate(pattern, agents, name?, version?, description?, adapter?) → str` |

!!! warning "`BlueprintCompiler` is a deprecated shim"
    `BlueprintCompiler().compile(spec)` still works but raises a `DeprecationWarning` — it now
    delegates internally to `PyAgentAdapter`. Use the [Runtime Adapters](#runtime-adapters) API
    (`AdapterRegistry.discover()["pyagent"]().compile(ir)`) directly in new code.

### Runtime Adapters

The subsystem behind [Adapters](adapters.md) — one `BlueprintIR` compiles unmodified onto any
registered adapter.

| Class / Function | Description |
|-------|-------------|
| `RuntimeAdapter` | Abstract base every adapter implements: `compile(ir) → CompiledArtifact`, always-async `run()` |
| `AdapterRegistry` | `.discover() → dict[str, type[RuntimeAdapter]]`, `.get(name)` |
| `AdapterResult` | Result of `adapter.run(...)` |
| `CompiledArtifact` | What `adapter.compile(ir)` returns — the runtime-native graph/crew/agent |
| `CompileDiagnostic` | Stable diagnostic code emitted when a governance feature isn't supported (e.g. `BUDGET_UNSUPPORTED`) |
| `Capability` | `Flag` enum describing what an adapter supports |
| `UnknownWorkflowError` | Raised when `run(workflow=...)` names a workflow the IR doesn't define |
| `render_adapter_template` / `write_adapter_template` | Scaffold a starter third-party `RuntimeAdapter` package |

### RuntimeGraph

| Method | Description |
|--------|-------------|
| `graph.run(workflow, input)` | Execute a named workflow |
| `graph.stream(workflow, input)` | Stream workflow execution |
| `graph.workflow_names` | List of compiled workflow names |
| `graph.agents` | Dict of all compiled agents |
| `graph.describe()` | Returns metadata dict |

### RuntimeGraph Hook Wiring

| Method | Targets | Hook |
|--------|---------|------|
| `graph.wire_trace(bus)` | All patterns + agents | `_trace_bus` |
| `graph.wire_context(ledger)` | All agents | `_context_ledger` |
| `graph.wire_compressor(compressor)` | All agents | `_compressor` |
| `graph.wire_cost_tracker(tracker)` | All agents | `_cost_tracker` |

### Schema Models (Pydantic)

| Model | Key Fields |
|-------|------------|
| `BlueprintSpec` | `api_version`, `metadata`, `providers`, `agents`, `workflows`, `contracts`, `observability`, `context` |
| `MetadataSpec` | Blueprint name, version, description |
| `AgentSpec` | `prompt`, `provider`, `guardrails` |
| `WorkflowSpec` | `pattern`, `agents` |
| `ProviderBindingSpec` | Named provider → model binding used by `providers:` |
| `ContractSpec` | `input`, `output`, `sla` |
| `ObservabilitySpec` | `tracing`, `cost_budget` |
| `ContextConfigSpec` | `memory`, `compression`, `redaction` |
| `PackageSpec` | Fields consumed by `package_blueprint()` when building an Agent Unit archive |

### Packaging

| Function / Class | Description |
|-------|-------------|
| `package_blueprint(...)` | Builds a distributable "Agent Unit" archive from a compiled spec |
| `AgentUnitMetadata` | Metadata embedded in a packaged Agent Unit |
| `PackagingError` | Raised on a packaging failure |

### Loader Functions

| Function | Description |
|----------|-------------|
| `load_blueprint(path)` | Load from a YAML file path |
| `load_blueprint_from_str(text, fmt="yaml")` | Load from a YAML/JSON string |

### CLI

```bash
pyagent-blueprint validate blueprint.yaml
pyagent-blueprint compile blueprint.yaml
pyagent-blueprint render blueprint.yaml --format mermaid
pyagent-blueprint test blueprint.yaml
pyagent-blueprint diff v1.yaml v2.yaml
pyagent-blueprint generate --pattern supervisor --agents a,b,c
pyagent-blueprint package blueprint.yaml          # build an Agent Unit archive
pyagent-blueprint adapters                        # list every registered RuntimeAdapter
pyagent-blueprint adapter-template my-adapter      # scaffold a starter RuntimeAdapter package
```

[→ Full pyagent-blueprint API reference](blueprint.md)

</div>

<div class="bib-section" markdown>

## pyagent-patterns
<span class="bib-source">[source ↗](https://github.com/pyagent-core/pyagent/blob/main/packages/pyagent-patterns/src/pyagent_patterns/)</span>

Core orchestration framework — agents, patterns, guardrails, recovery, and composition.

### Base Classes

| Class | Key Methods / Attributes | Description |
|-------|--------------------------|-------------|
| `Message` | `.user(content)`, `.system(content)`, `.assistant(content)`, `.role`, `.content` | Typed message with role enum |
| `Agent` | `.run(messages: list[Message]) → Message`, `.name`, `.system_prompt`, `.description` | LLM-backed callable agent |
| `Pattern` | `.run(input, context?)`, `.stream(input, context?)`, `._execute(ctx: Context) → Result`, `.pattern_type` | Base class for all orchestration patterns |
| `Context` | `.task`, `.metadata`, `.parent_id`, `.messages`, `.id`, `.child(task?)` | Shared execution context |
| `Result` | `.output`, `.messages`, `.metadata`, `.duration_seconds`, `.token_estimate`, `.cost_estimate` | Pattern execution result |
| `MockLLM` | `MockLLM(responses, delay?)` | Deterministic test double |
| `LLMCallable` | `async __call__(messages) -> str` | Protocol any LLM adapter must satisfy |

### Agent Hook Methods

| Method | Returns | Hook Attribute | Description |
|--------|---------|----------------|-------------|
| `agent.set_trace_bus(bus)` | `self` | `_trace_bus` | Wire TraceEventBus for `agent_start`/`agent_end` events |
| `agent.set_context(ledger)` | `self` | `_context_ledger` | Wire ContextLedger for read/write per call |
| `agent.set_compressor(compressor)` | `self` | `_compressor` | Wire MessageCompressor for output compression |
| `agent.set_cost_tracker(tracker)` | `self` | `_cost_tracker` | Wire CostTracker for token/cost recording |

### Pattern Hook Methods

| Method | Returns | Hook Attribute | Description |
|--------|---------|----------------|-------------|
| `pattern.set_trace_bus(bus)` | `self` | `_trace_bus` | Wire TraceEventBus for `pattern_start`/`pattern_end` events |

### Registry & Streaming

| Function / Class | Description |
|-------|-------------|
| `register_pattern(name, cls)` | Register a pattern class under a lookup name |
| `get_pattern_class(name)` | Resolve a registered pattern class by name (used by the Blueprint compiler) |
| `list_patterns()` | List every registered pattern name |
| `stream_pattern(pattern, task)` | Async-iterate a pattern's execution as it runs |
| `StreamChunk` | One chunk yielded by `stream_pattern` / `pattern.stream()` |

### Orchestration Patterns (Tier 1)

| Pattern | Constructor Params | Metadata Keys |
|---------|-------------------|---------------|
| `Pipeline` | `stages: list[Agent]` | `stages`, `stage_names` |
| `Supervisor` | `classifier, routes, formatter?, default_route?` | `route_key`, `classifier_output` |
| `FanOutFanIn` | `agents: list[Agent], aggregator: Agent` | `parallel_agents`, `agent_names` |
| `Hierarchical` | `manager: Agent, teams: list[Team]` | `teams`, `total_workers`, `team_names` |
| `OrchestratorWorkers` | `orchestrator: Agent, workers: list[Agent]` | `assignments`, `workers_used` |

### Resolution Patterns (Tier 2)

| Pattern | Constructor Params | Metadata Keys |
|---------|-------------------|---------------|
| `SelfReflection` | `agent, critic?, max_rounds?, stop_phrase?` | `rounds`, `max_rounds`, `early_stop` |
| `CrossReflection` | `generator, reviewer, max_rounds?, stop_phrase?` | `rounds`, `generator`, `reviewer` |
| `Debate` | `debaters, judge, rounds?, positions?` | `rounds`, `positions`, `debate_log` |
| `Voting` | `voters, strategy?, weights?, normalize?` | `strategy`, `votes`, `tally`, `winner` |
| `EvaluatorOptimizer` | `generator, evaluator, criteria, max_rounds?, pass_threshold?` | `rounds`, `scores`, `final_score`, `passed` |

### Structural Patterns (Tier 3)

| Pattern | Constructor Params | Metadata Keys |
|---------|-------------------|---------------|
| `RoleBased` | `agents, rounds?, shared_context?` | `rounds`, `roles`, `shared_context` |
| `Layered` | `layers: list[Layer]` | `layer_count`, `layer_names`, `agents_per_layer` |
| `Topology` | `agents, topology, hub_index?, rounds?` | `topology` |
| `Blackboard` | `agents: list[BlackboardAgent], rounds?, initial_state?` | `rounds`, `final_state` |

### Advanced Patterns (Tier 4)

| Pattern | Constructor Params | Metadata Keys |
|---------|-------------------|---------------|
| `TalkerReasoner` | `talker, reasoner, classifier?, complexity_threshold?` | `system`, `escalated` |
| `Swarm` | `agents, rounds?, neighbor_count?, aggregation?` | `agents`, `rounds`, `final_states` |
| `HumanInTheLoop` | `agent, review_fn, max_revisions?` | `approved`, `revisions`, `human_modified` |
| `ReAct` | `agent, tools: dict, max_steps?, finish_token?` | `steps`, `tools_used`, `trace` |

### Supporting Types

Types referenced by the constructors above, not full patterns on their own:

`Team` (Hierarchical) · `Layer` (Layered) · `TopologyType` enum: `CHAIN`, `STAR`, `MESH` (Topology) ·
`VotingStrategy` enum: `MAJORITY`, `WEIGHTED` (Voting) · `CircuitState` enum: `CLOSED`, `OPEN`,
`HALF_OPEN` (CircuitBreaker) · `BlackboardAgent` / `BlackboardState` / `BlackboardEntry` (Blackboard) ·
`Quality` / `Latency` / `Constraints` / `Recommendation` (PatternAdvisor)

### Guardrails

| Class | Constructor | Key Method |
|-------|-------------|------------|
| `GuardrailChain` | `GuardrailChain(guards)` | `.check(content) → GuardrailResult` |
| `PIIGuard` | `PIIGuard(redact=True)` | `.check(content)` — detects email, phone, SSN, credit card |
| `LengthGuard` | `LengthGuard(max_chars, truncate?)` | `.check(content)` — enforces length |
| `ContentGuard` | `ContentGuard(deny_words?, deny_patterns?)` | `.check(content)` — blocks forbidden content |

### Recovery

| Class | Constructor | Key Method |
|-------|-------------|------------|
| `BoundedExecution` | `BoundedExecution(pattern, fallback?, max_retries?, timeout_seconds?, max_tokens?)` | `.run(input)` — retry → fallback → degrade |
| `CircuitBreaker` | `CircuitBreaker(failure_threshold, reset_timeout_seconds, fallback_result?)` | `.execute(pattern, input)` — CLOSED → OPEN → HALF_OPEN |

### Composition & Advisor

| Class | Constructor | Key Method |
|-------|-------------|------------|
| `CompositePattern` | `CompositePattern(...)` | Nest patterns as stages/agents in other patterns |
| `PatternAdvisor` | `PatternAdvisor()` | `.recommend(task, constraints) → Recommendation` |

[→ Full pyagent-patterns API reference](patterns/base.md)

</div>

<div class="bib-section" markdown>

## pyagent-router
<span class="bib-source">[source ↗](https://github.com/pyagent-core/pyagent/blob/main/packages/pyagent-router/src/pyagent_router/)</span>

Difficulty-aware model selection, cost estimation, and routing middleware.

| Class | Constructor | Key Methods |
|-------|-------------|-------------|
| `ModelSelector` | `ModelSelector()` | `.select(task, required_capability?) → SelectionResult` |
| `DifficultyScorer` | `DifficultyScorer(custom_signals?)` | `.score(task) → DifficultyScore` |
| `CostEstimator` | `CostEstimator(pricing?)` | `.compare(text, models?) → list[CostEstimate]`, `.estimate_from_text(model, text)` |
| `RouterMiddleware` | `RouterMiddleware(model_registry, required_capability?, selector?)` | `.wrap(agent) → RoutedAgent`, `.wrap_all(agents)` |
| `Capability` | Enum | `CODE`, `MATH`, `REASONING`, `CREATIVE`, `GENERAL`, `VISION` |

### Return Types

| Type | Description |
|------|-------------|
| `SelectionResult` | What `ModelSelector.select()` returns — chosen model + reasoning |
| `DifficultyScore` | What `.score()` returns — `.is_easy` / `.is_medium` / `.is_hard` |
| `CostEstimate` | One model's cost estimate from `.compare()` |
| `ModelSpec` / `DEFAULT_MODEL_SPECS` | Built-in model catalog `ModelSelector` scores against |
| `RoutedAgent` | What `RouterMiddleware.wrap()` returns — exposes `.routing_log` |

[→ Full pyagent-router API reference](router.md)

</div>

<div class="bib-section" markdown>

## pyagent-providers
<span class="bib-source">[source ↗](https://github.com/pyagent-core/pyagent/blob/main/packages/pyagent-providers/src/pyagent_providers/)</span>

Multi-provider abstraction, registry, routing, fallback, capability negotiation, and cost optimization.

| Class | Constructor | Key Methods |
|-------|-------------|-------------|
| `ProviderProtocol` | (Protocol) | `.complete(messages, model?) → str`, `.__call__(messages) → str` |
| `ProviderRegistry` | `ProviderRegistry()` | `.register(name, provider)`, `.get(name)`, `.list_providers() → list[ProviderInfo]` |
| `ProviderRouter` | `ProviderRouter(registry, strategy)` | `.route(messages, required?) → (provider, model)` |
| `FallbackChain` | `FallbackChain(providers, circuit_breakers?)` | `.complete(messages) → FallbackResult` |
| `CapabilityNegotiator` | `CapabilityNegotiator(registry)` | `.negotiate(required?, min_context?, needs_streaming?, needs_tools?, needs_vision?) → NegotiationResult`, `.negotiate_all(...)` |
| `CostOptimizer` | `CostOptimizer(registry)` | `.compare(task, healthy_only?, limit?)`, `.cheapest(task, ...)`, `.cheapest_provider(task, ...)` |
| `TracedProvider` | `TracedProvider(provider, trace_bus)` | Wraps any provider; emits `provider_call_start/end/error` trace events |
| `MockProvider` | `MockProvider(name="mock", responses?, models?, capabilities?, max_context?, health_status?, delay?)` | Test double implementing `ProviderProtocol` |

### Concrete Adapters

| Class | Backend |
|-------|---------|
| `AnthropicProvider` | Anthropic API (degrades gracefully if `anthropic` isn't installed) |
| `OpenAIProvider` | OpenAI API |
| `LiteLLMProvider` | Any LiteLLM-supported backend |

### Routing Strategies

| Strategy | Description |
|----------|-------------|
| `capability_first` | First provider matching required capabilities |
| `cost_first` | Cheapest provider |
| `latency_first` | Lowest-latency provider |
| `round_robin` | Rotate across providers |

### Supporting Types

`HealthStatus` enum: `HEALTHY`, `DEGRADED`, `UNHEALTHY` · `ProviderCapabilities` / `ProviderInfo` ·
`FallbackResult` / `FallbackAttempt` · `NegotiationResult` · `ProviderCostEstimate`

[→ Full pyagent-providers API reference](providers.md)

</div>

<div class="bib-section" markdown>

## pyagent-compress
<span class="bib-source">[source ↗](https://github.com/pyagent-core/pyagent/blob/main/packages/pyagent-compress/src/pyagent_compress/)</span>

Inter-agent message compression, token budgets, and agent pruning.

| Class | Constructor | Key Methods |
|-------|-------------|-------------|
| `MessageCompressor` | `MessageCompressor(target_ratio, min_sentence_length?, remove_filler?)` | `.compress(text) → CompressionResult` |
| `CompressionResult` | (dataclass) | `.compressed`, `.original`, `.original_tokens`, `.compressed_tokens`, `.savings_pct` |
| `CompressMiddleware` | `CompressMiddleware(compressor?, budget?, target_ratio?)` | `.wrap(agent) → CompressedAgent`, `.wrap_all(agents)` |
| `TokenBudget` | `TokenBudget(workflow_limit, per_agent_limit?, strict?)` | `.consume(agent, tokens)`, `.remaining(agent?)`, `.summary()`, `.register_agent()`, `.total_used`, `.workflow_utilization` |
| `AgentPruner` | `AgentPruner(min_contribution, window_size?)` | `.score_agents(messages, task) → list[ContributionScore]`, `.should_prune(scores)` |
| `InteractionPruner` | `InteractionPruner(consensus_threshold, min_rounds?)` | `.has_consensus(outputs, current_round) → bool` |

### Supporting Types

`BudgetExceededError` (raised in `strict` mode) · `AgentBudget` (per-agent allocation) ·
`ContributionScore` (return type of `.score_agents()`) · `CompressedAgent` (return type of `.wrap()`)

[→ Full pyagent-compress API reference](compress.md)

</div>

<div class="bib-section" markdown>

## pyagent-context
<span class="bib-source">[source ↗](https://github.com/pyagent-core/pyagent/blob/main/packages/pyagent-context/src/pyagent_context/)</span>

Structured context with trust metadata, three-tier memory, compression, retrieval, and redaction.

| Class | Constructor | Key Methods |
|-------|-------------|-------------|
| `ContextItem` | `ContextItem(content, source, trust_level?, sensitivity?)` | `.content`, `.source`, `.trust_level`, `.sensitivity`, `.token_count`, `.id`, `.is_expired`, `.age_seconds`, `.to_dict()`/`.from_dict()` |
| `ContextLedger` | `ContextLedger()` | `.append(item)`, `.add(content, source, trust_level?)`, `.to_messages(budget?)`, `.items`, `.total_tokens`, `.query(...)`, `.snapshot()`, `.from_snapshot()`, `.clear()` |
| `WorkingMemory` | `WorkingMemory(max_items, max_tokens)` | `.add(item)`, `.items`, `.token_count`, `.utilization`, `.clear()` |
| `SessionMemory` | `SessionMemory(session_id, backend="json", storage_path=".pyagent_sessions")` | `.save(items)`, `.load() → list[ContextItem]` |
| `InMemorySemanticStore` | `InMemorySemanticStore()` | `.add(item)`, `.search(query, top_k) → list[ScoredItem]`, `.remove()`, `.clear()` |
| `ContextCompressor` | `ContextCompressor(policy, threshold_tokens?, floor_tokens?, preserve_trust?)` | `.compress(items, target_tokens) → list[ContextItem]`, `.should_compress()`, `.policy` |
| `TrustAwareRetriever` | `TrustAwareRetriever()` | `.retrieve(items, query, top_k) → list[ScoredItem]` |
| `ContextRedactor` | `ContextRedactor(max_sensitivity)` | `.redact_item(item)`, `.redact_ledger(ledger)` |
| `ContextLifecycle` | `ContextLifecycle()` | `.sweep_expired(ledger)`, `.apply_freshness_decay(ledger)`, `.consolidate(ledger, threshold)` |

### Enums

| Enum | Values |
|------|--------|
| `TrustLevel` | `VERIFIED`, `INFERRED`, `USER_PROVIDED`, `EXTERNAL` |
| `Sensitivity` | `PUBLIC`, `INTERNAL`, `CONFIDENTIAL`, `RESTRICTED` |

### Compression Policies

| Policy | Description |
|--------|-------------|
| `none` | No compression |
| `fifo` | Drop oldest items first |
| `semantic_lossless` | Preserve high-trust, drop redundant |
| `sawtooth` | Aggressive then gradual (preserves verified) |

### Supporting Types

`SearchResult` / `ScoredItem` (return type of `.search()` / `.retrieve()`) · `SemanticMemoryProtocol`
(protocol `InMemorySemanticStore` implements — bring your own vector backend)

[→ Full pyagent-context API reference](context.md)

</div>

<div class="bib-section" markdown>

## pyagent-trace
<span class="bib-source">[source ↗](https://github.com/pyagent-core/pyagent/blob/main/packages/pyagent-trace/src/pyagent_trace/)</span>

OpenTelemetry spans, TraceEventBus, cost tracking, record/replay, and exporters.

### Core Classes

| Class | Constructor | Key Methods |
|-------|-------------|-------------|
| `TraceEventBus` | `TraceEventBus()` | `.emit(event)`, `.subscribe(callback)`, `.subscribe_filter(types, callback)`, `.unsubscribe()`, `.emit_async()` |
| `TraceEvent` | (dataclass) | `.event_type`, `.agent_name`, `.pattern_type`, `.payload`, `.timestamp` |
| `CostTracker` | `CostTracker(event_bus?)` | `.record(pattern, agent, model, input_tokens, output_tokens, cost)`, `.total_cost`, `.total_tokens`, `.by_agent()`, `.by_model()`, `.by_pattern()`, `.summary()` |
| `CostEntry` | (dataclass) | `.pattern_name`, `.agent_name`, `.model`, `.input_tokens`, `.output_tokens`, `.cost_usd` |
| `Recorder` | `Recorder(event_bus?)` | `.start(pattern)`, `.record_llm_call(...)`, `.end(output)`, `.save(path)`, `.load(path)`, `.entries`, `.llm_calls` |
| `PatternSpanEmitter` | `PatternSpanEmitter()` | `.pattern_span(name, attrs?)`, `.agent_span(name, parent?)`, `.set_pattern_result(...)`, `.set_routing_info(...)`, `.set_compression_info(...)`, `.set_error(...)` |
| `TraceExporter` | (Protocol) | Interface every exporter below implements: `.export_event(event)` |

### Decorators

| Decorator | Usage | Description |
|-----------|-------|--------------|
| `@traced_pattern` | `@traced_pattern class MyPipeline(Pipeline): pass` | Auto-emit OTel span on every `.run()` |
| `traced_agent(agent)` | `agent = traced_agent(Agent(...))` | Wrap agent with OTel span emission |

### Exporters

| Exporter | Backend | Key Method |
|----------|---------|------------|
| `ConsoleExporter` | stdout | `.export_event(event)` |
| `JsonlExporter` | JSONL file | `.export_event(event)`, `.flush()` |
| `OTelExporter` | Jaeger / Tempo / Datadog / Honeycomb | `.export_event(event)`, `.shutdown()` |
| `LangfuseExporter` | Langfuse | `.export_event(event)`, `.flush()` |

### OTel Attributes (`pyagent.*` namespace)

`PyAgentAttributes` defines ~20 constants; the ones you'll reach for most:

| Attribute | Type | Description |
|-----------|------|-------------|
| `pyagent.pattern.type` | string | Pattern name |
| `pyagent.pattern.rounds` | int | Rounds executed |
| `pyagent.pattern.consensus` | bool | Whether a resolution pattern reached consensus |
| `pyagent.pattern.escalated` | bool | Whether TalkerReasoner escalated to the reasoner |
| `pyagent.agent.name` | string | Agent name |
| `pyagent.agent.role` | string | Agent role (structural patterns) |
| `pyagent.router.difficulty` | int | Difficulty 1–10 |
| `pyagent.router.selected_model` | string | Routed model |
| `pyagent.router.alternatives` | string | Other candidate models considered |
| `pyagent.compress.savings_pct` | float | Compression savings 0–1 |
| `pyagent.cost.total_usd` | float | Total cost USD |
| `pyagent.exec.duration_ms` | float | Duration in ms |
| `pyagent.exec.token_estimate` | int | Estimated tokens for the call |

[→ Full pyagent-trace API reference](trace.md)

</div>

<div class="bib-section" markdown>

## pyagent-studio
<span class="bib-source">[source ↗](https://github.com/pyagent-core/pyagent/blob/main/packages/pyagent-studio/src/pyagent_studio/)</span>

CLI + web control plane for agent blueprints. Installs as the `pyagent` command.

### CLI Commands

| Command | Description |
|---------|-------------|
| `pyagent apply <file>` | Load, validate, summarize |
| `pyagent validate <file>` | Validate a blueprint |
| `pyagent test <file>` | Contract conformance vs. MockLLM |
| `pyagent simulate <file> <workflow> <input>` | Run a workflow with MockLLM |
| `pyagent simulate <file> <workflow> <input> --live` | Run a workflow with real LLMs |
| `pyagent diff <old> <new>` | Semantic diff between two blueprint versions |
| `pyagent render <file> [--format]` | Render to Mermaid or Markdown |
| `pyagent generate --pattern <p> --agents <a,b,c>` | Scaffold a starter blueprint |
| `pyagent get <resource> <file>` | Inspect `agents`, `workflows`, `providers`, or `contracts` |
| `pyagent describe <file>` | Print blueprint metadata |
| `pyagent providers list` | List registered providers |
| `pyagent providers health [--model]` | Provider health check |
| `pyagent dashboard` | Launch the web UI |

### Headless Services

| Service | Key Methods |
|---------|--------------|
| `BlueprintService` | `.load(path)`, `.validate()`, `.compile()`, `.discover_blueprints()`, `.summary()`, `.spec`/`.graph`/`.path` |
| `SimulationService` | `.run(spec, workflow, input)`, `.run_all()` |
| `GovernanceService` | `.check_compliance(spec)`, `.format_report(report)`, `.diff()`, `.diff_summary()` |
| `TraceService` | `.load(path)`, `.summary()`, `.query()` |

### Web Dashboard Pages

| Page | Description |
|------|-------------|
| Overview | Blueprint summary, validation status, quick actions |
| Agents | Agent table with prompts, providers, guardrails |
| Workflows | Workflow DAGs with Mermaid diagrams |
| Simulate | Run workflows with MockLLM or live providers |
| Traces | Live SSE trace stream + historical JSONL viewer |
| Governance | Compliance score, validation issues, blueprint diff |
| Providers | LLM model catalog, health checks |
| Diff | Side-by-side semantic diff between two blueprint versions |
| Docs | In-app rendering of this documentation site |

[→ Full pyagent-studio API reference](studio.md)

</div>

<div class="bib-section" markdown>

## Hook Event Reference

Complete list of trace events emitted by all hooks:

| Event Type | Emitter | When | Payload |
|------------|---------|------|---------|
| `agent_start` | `Agent` | Before LLM call | `agent_name`, `input` |
| `agent_end` | `Agent` | After LLM call + hooks | `agent_name`, `output`, `duration_seconds`, `output_tokens` |
| `pattern_start` | `Pattern` | Before `_execute()` | `pattern_type`, `input` |
| `pattern_end` | `Pattern` | After `_execute()` | `pattern_type`, `output_length`, `duration_seconds`, `token_estimate` |
| `compression` | `Agent` (compressor) | After output compression | `agent_name`, `original_tokens`, `compressed_tokens`, `savings_pct` |
| `provider_call_start` | `TracedProvider` | Before provider call | `provider_name`, `model`, `message_count` |
| `provider_call_end` | `TracedProvider` | After provider call | `provider_name`, `model`, `duration_seconds`, `output_length` |
| `provider_call_error` | `TracedProvider` | On provider error | `provider_name`, `model`, `error` |
| `cost_recorded` | `CostTracker` | After cost entry added | `pattern`, `agent`, `model`, `cost_usd`, `tokens` |
| `llm_call` | `Recorder` | After recording a call | `agent_name`, `response`, `metadata` |

</div>

<div class="bib-section" markdown>

## Cross-Package Integration Matrix

Shows which packages interact and how:

| Producer | Consumer | Integration Point |
|----------|----------|-------------------|
| `pyagent-patterns` | `pyagent-trace` | `Agent.set_trace_bus()`, `Pattern.set_trace_bus()` |
| `pyagent-patterns` | `pyagent-context` | `Agent.set_context()` |
| `pyagent-patterns` | `pyagent-compress` | `Agent.set_compressor()` |
| `pyagent-patterns` | `pyagent-trace` | `Agent.set_cost_tracker()` |
| `pyagent-providers` | `pyagent-trace` | `TracedProvider(provider, trace_bus)` |
| `pyagent-router` | `pyagent-patterns` | `RouterMiddleware.wrap(agent)` |
| `pyagent-compress` | `pyagent-patterns` | `CompressMiddleware.wrap(agent)` |
| `pyagent-blueprint` | `pyagent-patterns` | `RuntimeAdapter.compile()` creates Agents + Patterns |
| `pyagent-blueprint` | `pyagent-trace` | `RuntimeGraph.wire_trace()` |
| `pyagent-blueprint` | `pyagent-context` | `RuntimeGraph.wire_context()` |
| `pyagent-blueprint` | `pyagent-compress` | `RuntimeGraph.wire_compressor()` |
| `pyagent-blueprint` | `pyagent-trace` | `RuntimeGraph.wire_cost_tracker()` |
| `pyagent-trace` | `pyagent-studio` | `TraceEventBus` feeds Studio dashboard |

</div>

</div>
