# pyagent-patterns

**18 reusable multi-agent orchestration patterns for LLMs** — zero dependencies, async-first, fully typed.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](../../LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

## Install

```bash
pip install pyagent-patterns
```

## Core Concepts

```python
from pyagent_patterns.base import Agent, Message, Context, Result, MockLLM

# Agent: wraps any LLM with a name and system prompt
agent = Agent(
    name="analyst",
    llm=your_llm,  # any async callable: (list[Message]) -> str
    system_prompt="You are a senior analyst.",
    description="Optional description for pattern advisors and registries.",
)

# Every pattern has the same interface
result: Result = await pattern.run("Your task")

# Result fields
result.output              # str — final text
result.messages            # list[Message] — full conversation
result.metadata            # dict — pattern-specific (rounds, route, scores, etc.)
result.duration_seconds    # float — wall-clock time
result.token_estimate      # int — rough token count
```

## Pattern Catalog

| Tier | Patterns | Best For |
|------|----------|----------|
| **Orchestration** | Pipeline, Supervisor, Fan-Out/Fan-In, Hierarchical, Orchestrator-Workers | Sequential processing, routing, parallel analysis, enterprise workflows |
| **Resolution** | Self-Reflection, Cross-Reflection, Debate, Voting, Evaluator-Optimizer | Code gen, peer review, adversarial decisions, consensus, quality iteration |
| **Structural** | Role-Based, Layered, Topology, Blackboard | Team simulation, multi-level analysis, communication topology, shared state |
| **Advanced** | Talker-Reasoner, Swarm, Human-in-the-Loop, ReAct | Cost-optimized chat, emergent behavior, safety-critical, tool-using agents |

## Examples

### Pipeline — Sequential Processing

```python
import asyncio
from pyagent_patterns.base import Agent, MockLLM
from pyagent_patterns.orchestration import Pipeline

llm = MockLLM(responses=[
    "Extracted: Revenue $25.2B, margin 17.1%, storage +73% YoY",
    "Facts: Revenue (+8% YoY verified), margin (in-line with guidance), storage (record quarter)",
    "Tesla Q3 2025: Record revenue of $25.2B driven by 73% energy storage growth...",
])

pipeline = Pipeline(stages=[
    Agent("extractor", llm, system_prompt="Extract claims, figures, and entities."),
    Agent("fact_checker", llm, system_prompt="Verify which items are facts vs opinions."),
    Agent("writer", llm, system_prompt="Write a concise brief."),
])

result = asyncio.run(pipeline.run("Tesla Q3 2025 earnings transcript..."))
print(result.output)
print(result.metadata)  # {"stages": 3, "stage_names": ["extractor", "fact_checker", "writer"]}
```

### Debate — Adversarial Argumentation

```python
from pyagent_patterns.resolution import Debate
from pyagent_patterns.base import Agent, MockLLM

llm = MockLLM(responses=[
    "Build: Full control, competitive differentiation, lower long-term cost...",
    "Buy: 6 months faster to market, proven reliability, team stays focused...",
    "Build: Vendor lock-in risk outweighs speed. Our data shows...",
    "Buy: Engineering cost of maintenance alone exceeds vendor fees...",
    "Build: Custom optimisation impossible with vendor. Our benchmarks...",
    "Buy: Vendor R&D budget is 100x ours. We can't keep up...",
    "VERDICT: Buy for initial launch, plan migration to custom solution in 18 months...",
])

debate = Debate(
    debaters=[
        Agent("build_advocate", llm, system_prompt="Argue for building in-house."),
        Agent("buy_advocate", llm, system_prompt="Argue for a vendor solution."),
    ],
    judge=Agent("cto", llm, system_prompt="Render a verdict based on arguments presented."),
    rounds=3,
    positions=["BUILD", "BUY"],
)

result = asyncio.run(debate.run("Should we build or buy our vector database?"))
print(result.metadata["rounds"])       # 3
print(result.metadata["debate_log"])   # full argument history
```

### ReAct — Tool-Using Agent

```python
from pyagent_patterns.advanced import ReAct
from pyagent_patterns.base import Agent, MockLLM

def calculator(expression: str) -> str:
    return str(eval(expression))

def lookup(key: str) -> str:
    data = {"NVDA_PE": "65.2", "AMD_PE": "120.4", "INTC_PE": "28.1"}
    return data.get(key, "Not found")

llm = MockLLM(responses=[
    "Thought: I need P/E ratios.\nAction: lookup\nInput: NVDA_PE",
    "Thought: Got NVDA. Now AMD.\nAction: lookup\nInput: AMD_PE",
    "Thought: Got AMD. Now Intel.\nAction: lookup\nInput: INTC_PE",
    "Thought: I have all data. Intel is cheapest at 28.1x.\nFINISH",
])

react = ReAct(
    agent=Agent("analyst", llm, system_prompt="Research financial data using tools."),
    tools={"calculator": calculator, "lookup": lookup},
    max_steps=6,
    finish_token="FINISH",
)

result = asyncio.run(react.run("Compare NVDA, AMD, INTC P/E ratios"))
print(result.metadata["steps"])       # 4
print(result.metadata["tools_used"])  # ["lookup", "lookup", "lookup"]
```

## CompositePattern — Escalation Chains

Chain multiple patterns with quality-based escalation. If the first pattern's output fails a quality check, escalate to the next.

```python
from pyagent_patterns.composite import CompositePattern
from pyagent_patterns.orchestration import Pipeline
from pyagent_patterns.resolution import SelfReflection

llm = MockLLM(responses=["Quick draft", "Thorough analysis with citations and examples"])

composite = CompositePattern(
    patterns=[
        Pipeline(stages=[Agent("fast_writer", llm)]),          # try cheap first
        SelfReflection(agent=Agent("careful_writer", llm)),    # escalate if needed
    ],
    quality_check=lambda result: len(result.output) > 50,  # simple length check
)

result = asyncio.run(composite.run("Write a technical guide on connection pooling"))
print(result.metadata["escalation_log"])  # shows which patterns ran and why
```

## PatternAdvisor — Auto-Select the Best Pattern

```python
from pyagent_patterns.advisor import PatternAdvisor, Constraints, Quality

advisor = PatternAdvisor()

rec = advisor.recommend(
    "Write and refine a technical guide",
    Constraints(quality=Quality.HIGH),
)
print(rec.pattern)              # "self_reflection"
print(rec.reason)               # "High quality creative/code task → generate-critique-refine loop"
print(rec.estimated_calls)      # 4
print(rec.estimated_cost_range) # "$0.004-0.012"
print(rec.alternatives)         # ["cross_reflection", "evaluator_optimizer"]

# Cost-sensitive
rec = advisor.recommend("Answer support questions", Constraints(max_cost_usd=0.005))
print(rec.pattern)  # "talker_reasoner"

# Fault-tolerant
rec = advisor.recommend("Medical diagnosis", Constraints(quality=Quality.CRITICAL, fault_tolerant=True))
print(rec.pattern)  # "voting"
```

## Guardrails — Validate Agent I/O

```python
from pyagent_patterns.guardrails import GuardrailChain, PIIGuard, LengthGuard, ContentGuard

# PIIGuard: detect and redact personal data
pii = PIIGuard(redact=True)
result = pii.check("Contact john@example.com or call 555-123-4567")
print(result.sanitized_content)  # "Contact [REDACTED-EMAIL] or call [REDACTED-PHONE]"

# ContentGuard: block forbidden terms
content = ContentGuard(deny_words=["confidential", "internal roadmap"])

# Chain: all must pass, sanitized content flows through
chain = GuardrailChain([
    PIIGuard(redact=True),
    LengthGuard(max_chars=3000, truncate=True),
    ContentGuard(deny_words=["confidential"]),
])

result = chain.check("Email john@co.com: the report is ready.")
if result.passed:
    print(result.sanitized_content)  # PII redacted, length OK, no forbidden terms
```

## Recovery — Production Resilience

```python
from pyagent_patterns.recovery import BoundedExecution, CircuitBreaker

# Three-level: retry → fallback → graceful degradation
bounded = BoundedExecution(
    pattern=Pipeline(stages=[Agent("primary", llm)]),
    fallback=Pipeline(stages=[Agent("backup", cheap_llm)]),
    max_retries=2,
    timeout_seconds=30.0,
    max_tokens=50_000,
)

result = asyncio.run(bounded.run("Complex task"))
print(result.metadata["recovery_level"])  # 0=primary, 1=fallback, 2=degraded

# Circuit breaker: prevent cascading failures
circuit = CircuitBreaker(failure_threshold=3, reset_timeout_seconds=60.0)
result = asyncio.run(circuit.execute(my_pattern, "task"))
print(circuit.state)  # CLOSED | OPEN | HALF_OPEN
```

## Pattern Registry

```python
from pyagent_patterns.registry import get_pattern_class, list_patterns, register_pattern

# All 18 built-in patterns are auto-registered
print(list_patterns())
# ["pipeline", "supervisor", "fan_out_fan_in", "hierarchical", ..., "react"]

# Look up by name (useful for spec-driven instantiation)
PipelineClass = get_pattern_class("pipeline")
pattern = PipelineClass(stages=[...])

# Register custom patterns
register_pattern("my_custom_pattern", MyCustomPattern)
```

## Streaming

```python
from pyagent_patterns.streaming import stream_pattern

async def stream_example():
    pipeline = Pipeline(stages=[
        Agent("extractor", llm),
        Agent("writer", llm),
    ])
    async for chunk in stream_pattern(pipeline, "Process this document"):
        print(chunk)  # StreamChunk with stage info and partial output

asyncio.run(stream_example())
```

## Testing Without API Calls

```python
from pyagent_patterns.base import MockLLM

# Returns responses in order, cycling when exhausted
llm = MockLLM(responses=["response 1", "response 2"])

# Simulate latency
llm = MockLLM(responses=["slow response"], delay=0.5)

# Echo mode (no responses = echo last user message)
llm = MockLLM()
```

## Full Documentation

See [pyagent.dev](https://pyagent.dev) for Mermaid sequence diagrams, full API reference, cookbook, and benchmarks.
