---
description: "Define workflows in a PyAgent blueprint — bind orchestration patterns to agents and routes."
---

# Blueprint — Workflows

Each entry under `workflows:` defines a named workflow — an orchestration pattern with agents wired to specific roles.

---

## WorkflowSpec Fields

```yaml
workflows:
  my_workflow:
    pattern: supervisor     # Required — registered pattern name
    agents: {}              # Pattern-specific agent mapping
    config: {}              # Optional pattern-level settings
    recovery:               # Optional failure handling
      max_retries: 2
      timeout_seconds: 30.0
      fallback_provider: fast
```

---

## Pattern Names

The `pattern` field must match a registered pattern. The built-in patterns from `pyagent-patterns`:

| Pattern | Key |
|---------|-----|
| Pipeline | `pipeline` |
| Supervisor | `supervisor` |
| Fan-Out / Fan-In | `fan_out_fan_in` |
| Hierarchical | `hierarchical` |
| Orchestrator-Workers | `orchestrator_workers` |
| Self-Reflection | `self_reflection` |
| Cross-Reflection | `cross_reflection` |
| Debate | `debate` |
| Voting | `voting` |
| Evaluator-Optimizer | `evaluator_optimizer` |
| Role-Based | `role_based` |
| Layered | `layered` |
| Topology | `topology` |
| Blackboard | `blackboard` |
| Talker-Reasoner | `talker_reasoner` |
| Swarm | `swarm` |
| Human-in-the-Loop | `human_in_the_loop` |
| ReAct | `react` |

The `BlueprintValidator` raises an error if the pattern key is not recognized.

---

## Agent Mappings by Pattern

### pipeline

```yaml
workflows:
  analysis:
    pattern: pipeline
    agents:
      stages: [extractor, analyst, writer]   # Ordered list of agent names
```

### supervisor

```yaml
workflows:
  support:
    pattern: supervisor
    agents:
      classifier: classifier          # The routing agent
      routes:                         # Route key → agent name
        billing: billing_agent
        technical: technical_agent
        returns: returns_agent
        general: general_agent
      formatter: formatter            # Optional post-processing agent
    config:
      default_route: general          # Fallback if classifier output isn't a key
```

### fan_out_fan_in

```yaml
workflows:
  market_analysis:
    pattern: fan_out_fan_in
    agents:
      agents: [fundamentals, technicals, sentiment]  # Run in parallel
      aggregator: synthesis_agent                    # Merge results
```

### debate

```yaml
workflows:
  review:
    pattern: debate
    agents:
      agents: [proposer, critic]     # Alternate turns
      judge: arbitrator              # Final verdict
    config:
      rounds: 2
```

### voting

```yaml
workflows:
  classification:
    pattern: voting
    agents:
      voters: [expert_1, expert_2, expert_3]
    config:
      strategy: majority             # majority | unanimous | weighted
```

### evaluator_optimizer

```yaml
workflows:
  writing:
    pattern: evaluator_optimizer
    agents:
      generator: writer_agent
      evaluator: critic_agent
    config:
      max_rounds: 3
      score_threshold: 8
```

### self_reflection

```yaml
workflows:
  coding:
    pattern: self_reflection
    agents:
      agent: coder_agent
    config:
      max_rounds: 3
```

### react

```yaml
workflows:
  research:
    pattern: react
    agents:
      agent: researcher
    config:
      max_steps: 10
```

---

## Recovery Config

Recovery handles infrastructure failures (API errors, timeouts, token limits). It is separate from quality-based escalation — see the [Composition Guide](../../guides/composition.md).

```yaml
workflows:
  main:
    pattern: supervisor
    agents: ...
    recovery:
      max_retries: 2             # Retry this many times before escalating
      timeout_seconds: 30.0     # Per-attempt wall-clock timeout
      fallback_provider: fast   # Use this cheaper provider if retries exhaust
```

| Field | Default | Description |
|-------|---------|-------------|
| `max_retries` | `0` | Number of retries before failing or using fallback |
| `timeout_seconds` | `null` | Per-attempt timeout; null = no limit |
| `fallback_provider` | `null` | Provider key to use when retries exhaust |

### Fallback provider behavior

When `fallback_provider` is set and all retries are exhausted, the compiler substitutes that provider for all agents in the workflow and tries one final time. This lets you degrade gracefully to a cheap model rather than returning an error.

---

## Multiple Workflows

A blueprint can have many named workflows — different entry points for different use cases, all sharing the same agents and providers:

```yaml
agents:
  fast_analyst:  { provider: fast,   prompt: "Quick analysis." }
  deep_analyst:  { provider: expert, prompt: "Deep analysis with citations." }
  writer:        { provider: fast,   prompt: "Write a report." }

workflows:
  quick:
    pattern: pipeline
    agents:
      stages: [fast_analyst, writer]

  deep:
    pattern: self_reflection
    agents:
      agent: deep_analyst
    config:
      max_rounds: 3
```

```python
graph = BlueprintCompiler().compile(spec)

quick_result = asyncio.run(graph.run("quick", task))
deep_result  = asyncio.run(graph.run("deep",  task))
```

---

## See Also

- [Agents](agents.md) — defining agents referenced in workflows
- [Patterns Package](../patterns/index.md) — pattern semantics and agent roles
- [Full Spec Reference](spec-format.md)
