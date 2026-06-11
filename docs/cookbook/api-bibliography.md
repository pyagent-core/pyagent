# API & Hooks Bibliography

**Complete reference of every public class, method, hook, and protocol across all pyagent-\* packages.**

Use this page as a quick-lookup cheat sheet. Each entry links to the detailed API Reference page and shows the signature at a glance.

---

## pyagent-patterns

Core orchestration framework — agents, patterns, guardrails, recovery, and composition.

### Base Classes

| Class | Key Methods / Attributes | Description |
|-------|--------------------------|-------------|
| `Message` | `.user(content)`, `.system(content)`, `.assistant(content)`, `.role`, `.content` | Typed message with role enum |
| `Agent` | `.run(input, context?)`, `.name`, `.system_prompt`, `.description` | LLM-backed callable agent |
| `Pattern` | `.run(input, context?)`, `.stream(input, context?)`, `._execute(input, context)` | Base class for all orchestration patterns |
| `Context` | `.task`, `.metadata`, `.parent_results` | Shared execution context |
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
| `TalkerReasoner` | `talker, reasoner, complexity_threshold?, classifier?` | `system`, `escalated` |
| `Swarm` | `agents, rounds?, neighbor_count?, aggregation?` | `agents`, `rounds`, `final_states` |
| `HumanInTheLoop` | `agent, review_fn, max_revisions?` | `approved`, `revisions`, `human_modified` |
| `ReAct` | `agent, tools: dict, max_steps?, finish_token?` | `steps`, `tools_used`, `trace` |

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

| Class | Key Method |
|-------|------------|
| `CompositePattern` | Nest patterns as stages/agents in other patterns |
| `PatternAdvisor` | `.recommend(task, constraints) → Recommendation` |

---

## pyagent-router

Difficulty-aware model selection, cost estimation, and routing middleware.

| Class | Constructor | Key Methods |
|-------|-------------|-------------|
| `ModelSelector` | `ModelSelector()` | `.select(task, required_capability?) → SelectionResult` |
| `DifficultyScorer` | `DifficultyScorer(custom_signals?)` | `.score(task) → DifficultyResult` |
| `CostEstimator` | `CostEstimator(pricing?)` | `.compare(task) → list[CostEstimate]`, `.estimate_from_text(model, task)` |
| `RouterMiddleware` | `RouterMiddleware(model_registry, required_capability?)` | `.wrap(agent)`, `.wrap_all(agents)` |
| `Capability` | Enum | `REASONING`, `CODE`, `VISION`, `FUNCTION_CALLING`, `STREAMING` |

---

## pyagent-compress

Inter-agent message compression, token budgets, and agent pruning.

| Class | Constructor | Key Methods |
|-------|-------------|-------------|
| `MessageCompressor` | `MessageCompressor(target_ratio, min_sentence_length?, remove_filler?)` | `.compress(text) → CompressionResult` |
| `CompressionResult` | (dataclass) | `.compressed`, `.original_tokens`, `.compressed_tokens`, `.savings_pct` |
| `CompressMiddleware` | `CompressMiddleware(compressor?, budget?)` | `.wrap(agent) → CompressedAgent` |
| `TokenBudget` | `TokenBudget(workflow_limit, per_agent_limit?, strict?)` | `.consume(agent, tokens)`, `.remaining(agent?)`, `.summary()` |
| `AgentPruner` | `AgentPruner(min_contribution, window_size?)` | `.score_agents(messages, task) → list[ContributionScore]`, `.should_prune(scores)` |
| `InteractionPruner` | `InteractionPruner(consensus_threshold, min_rounds?)` | `.has_consensus(outputs, current_round) → bool` |

---

## pyagent-trace

OpenTelemetry spans, TraceEventBus, cost tracking, record/replay, and exporters.

### Core Classes

| Class | Constructor | Key Methods |
|-------|-------------|-------------|
| `TraceEventBus` | `TraceEventBus()` | `.emit(event)`, `.subscribe(callback)`, `.subscribe_filter(types, callback)` |
| `TraceEvent` | (dataclass) | `.event_type`, `.agent_name`, `.pattern_type`, `.payload`, `.timestamp` |
| `CostTracker` | `CostTracker(event_bus?)` | `.record(pattern, agent, model, input_tokens, output_tokens, cost)`, `.total_cost`, `.by_agent()`, `.by_model()`, `.by_pattern()`, `.summary()` |
| `CostEntry` | (dataclass) | `.pattern_name`, `.agent_name`, `.model`, `.input_tokens`, `.output_tokens`, `.cost_usd` |
| `Recorder` | `Recorder(event_bus?)` | `.start(pattern)`, `.record_llm_call(...)`, `.end(output)`, `.save(path)`, `.load(path)` |
| `PatternSpanEmitter` | `PatternSpanEmitter()` | `.pattern_span(name, attrs?)`, `.agent_span(name, parent?)`, `.set_pattern_result(...)`, `.set_routing_info(...)`, `.set_compression_info(...)` |

### Decorators

| Decorator | Usage | Description |
|-----------|-------|-------------|
| `@traced_pattern` | `@traced_pattern class MyPipeline(Pipeline): pass` | Auto-emit OTel span on every `.run()` |
| `traced_agent(agent)` | `agent = traced_agent(Agent(...))` | Wrap agent with OTel span emission |

### Exporters

| Exporter | Backend | Key Method |
|----------|---------|------------|
| `ConsoleExporter` | stdout | `.export_event(event)` |
| `JsonlExporter` | JSONL file | `.export_event(event)`, `.flush()` |
| `OTelExporter` | Jaeger / Tempo / Datadog / Honeycomb | `.export_event(event)` |
| `LangfuseExporter` | Langfuse | `.export_event(event)` |

### OTel Attributes (`pyagent.*` namespace)

| Attribute | Type | Description |
|-----------|------|-------------|
| `pyagent.pattern.type` | string | Pattern name |
| `pyagent.pattern.rounds` | int | Rounds executed |
| `pyagent.agent.name` | string | Agent name |
| `pyagent.router.difficulty` | int | Difficulty 1–10 |
| `pyagent.router.selected_model` | string | Routed model |
| `pyagent.compress.savings_pct` | float | Compression savings 0–1 |
| `pyagent.cost.total_usd` | float | Total cost USD |
| `pyagent.exec.duration_ms` | float | Duration in ms |

---

## pyagent-providers

Multi-provider abstraction, registry, routing, fallback, capability negotiation, and cost optimization.

| Class | Constructor | Key Methods |
|-------|-------------|-------------|
| `ProviderProtocol` | (Protocol) | `.complete(messages, **kwargs) → CompletionResult`, `.__call__(messages) → str` |
| `ProviderRegistry` | `ProviderRegistry()` | `.register(name, provider)`, `.get(name)`, `.list()` |
| `ProviderRouter` | `ProviderRouter(registry, strategy)` | `.route(messages, required?) → (provider, model)` |
| `FallbackChain` | `FallbackChain(providers)` | `.complete(messages) → CompletionResult` |
| `CapabilityNegotiator` | `CapabilityNegotiator(registry)` | `.find(required) → list[provider]` |
| `CostOptimizer` | `CostOptimizer(registry)` | `.rank_by_cost(prompt_tokens, completion_tokens) → list` |
| `TracedProvider` | `TracedProvider(provider, event_bus)` | Wraps any provider; emits `provider_call_start/end/error` trace events |
| `MockProvider` | `MockProvider(name, model)` | Test double implementing `ProviderProtocol` |

### Routing Strategies

| Strategy | Description |
|----------|-------------|
| `capability_first` | First provider matching required capabilities |
| `cost_first` | Cheapest provider |
| `latency_first` | Lowest-latency provider |
| `round_robin` | Rotate across providers |

---

## pyagent-context

Structured context with trust metadata, three-tier memory, compression, retrieval, and redaction.

| Class | Constructor | Key Methods |
|-------|-------------|-------------|
| `ContextItem` | `ContextItem(content, source, trust?, sensitivity?)` | `.content`, `.source`, `.trust`, `.sensitivity`, `.token_count` |
| `ContextLedger` | `ContextLedger()` | `.append(item)`, `.add(content, source, trust_level?)`, `.to_messages(budget?)`, `.items`, `.total_tokens` |
| `WorkingMemory` | `WorkingMemory(max_items, max_tokens)` | `.add(item)`, `.items`, `.token_count` |
| `SessionMemory` | `SessionMemory(backend, path)` | `.save(items)`, `.load() → list[ContextItem]` |
| `InMemorySemanticStore` | `InMemorySemanticStore()` | `.add(item)`, `.search(query, top_k) → list` |
| `ContextCompressor` | `ContextCompressor(policy)` | `.compress(items, target_tokens) → list[ContextItem]` |
| `TrustAwareRetriever` | `TrustAwareRetriever()` | `.retrieve(items, query, top_k) → list` |
| `ContextRedactor` | `ContextRedactor(max_sensitivity)` | `.redact(items) → list[ContextItem]` |
| `ContextLifecycle` | `ContextLifecycle()` | `.sweep_expired(ledger)`, `.apply_freshness_decay(ledger)`, `.consolidate(ledger, threshold)` |

### Enums

| Enum | Values |
|------|--------|
| `TrustLevel` | `VERIFIED`, `INFERRED`, `USER_PROVIDED`, `UNVERIFIED` |
| `Sensitivity` | `PUBLIC`, `INTERNAL`, `CONFIDENTIAL`, `PII` |

### Compression Policies

| Policy | Description |
|--------|-------------|
| `none` | No compression |
| `fifo` | Drop oldest items first |
| `semantic_lossless` | Preserve high-trust, drop redundant |
| `sawtooth` | Aggressive then gradual (preserves verified) |

---

## pyagent-blueprint

Declarative YAML specs — validate, compile, test, diff, render, scaffold.

### Core Classes

| Class | Constructor | Key Methods |
|-------|-------------|-------------|
| `BlueprintCompiler` | `BlueprintCompiler()` | `.compile(spec) → RuntimeGraph` |
| `BlueprintValidator` | `BlueprintValidator()` | `.validate(spec) → list[ValidationIssue]` |
| `BlueprintRenderer` | `BlueprintRenderer()` | `.to_mermaid(spec)`, `.to_markdown(spec)` |
| `BlueprintDiffer` | `BlueprintDiffer()` | `.diff(old, new) → list[Change]`, `.summary(changes)` |
| `BlueprintTester` | `BlueprintTester()` | `.test(spec) → list[TestResult]` |
| `BlueprintGenerator` | `BlueprintGenerator()` | `.generate(pattern, agents) → str` |

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
| `AgentSpec` | `prompt`, `provider`, `guardrails` |
| `WorkflowSpec` | `pattern`, `agents` |
| `ContractSpec` | `input`, `output`, `sla` |
| `ObservabilitySpec` | `tracing`, `cost_budget` |
| `ContextConfigSpec` | `memory`, `compression`, `redaction` |

### Loader Functions

| Function | Description |
|----------|-------------|
| `load_blueprint(path)` | Load from YAML file |
| `load_blueprint_from_str(yaml_str)` | Load from YAML string |

### CLI

```bash
pyagent-blueprint validate blueprint.yaml
pyagent-blueprint compile blueprint.yaml
pyagent-blueprint render blueprint.yaml --format mermaid
pyagent-blueprint test blueprint.yaml
pyagent-blueprint diff v1.yaml v2.yaml
pyagent-blueprint generate --pattern supervisor --agents a,b,c
```

---

## pyagent-studio

CLI + web control plane for agent blueprints.

### CLI Commands

| Command | Description |
|---------|-------------|
| `pyagent apply <file>` | Load, validate, summarize |
| `pyagent simulate <file> <workflow> <input>` | Run with MockLLM |
| `pyagent simulate <file> <workflow> <input> --live` | Run with real LLMs |
| `pyagent dashboard` | Launch web UI |

### Headless Services

| Service | Key Methods |
|---------|-------------|
| `BlueprintService` | `.load(path)`, `.validate()` |
| `SimulationService` | `.run(spec, workflow, input)` |
| `GovernanceService` | `.check_compliance(spec)`, `.format_report(report)` |
| `TraceService` | `.load(path)`, `.summary()` |

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

---

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

---

## Cross-Package Integration Matrix

Shows which packages interact and how:

| Producer | Consumer | Integration Point |
|----------|----------|-------------------|
| `pyagent-patterns` | `pyagent-trace` | `Agent.set_trace_bus()`, `Pattern.set_trace_bus()` |
| `pyagent-patterns` | `pyagent-context` | `Agent.set_context()` |
| `pyagent-patterns` | `pyagent-compress` | `Agent.set_compressor()` |
| `pyagent-patterns` | `pyagent-trace` | `Agent.set_cost_tracker()` |
| `pyagent-providers` | `pyagent-trace` | `TracedProvider(provider, bus)` |
| `pyagent-blueprint` | `pyagent-patterns` | `BlueprintCompiler` creates Agents + Patterns |
| `pyagent-blueprint` | `pyagent-trace` | `RuntimeGraph.wire_trace()` |
| `pyagent-blueprint` | `pyagent-context` | `RuntimeGraph.wire_context()` |
| `pyagent-blueprint` | `pyagent-compress` | `RuntimeGraph.wire_compressor()` |
| `pyagent-blueprint` | `pyagent-trace` | `RuntimeGraph.wire_cost_tracker()` |
| `pyagent-trace` | `pyagent-studio` | `TraceEventBus` feeds Studio dashboard |
| `pyagent-router` | `pyagent-patterns` | `RouterMiddleware.wrap(agent)` |
| `pyagent-compress` | `pyagent-patterns` | `CompressMiddleware.wrap(agent)` |
