# pyagent-blueprint → Framework-Agnostic Agent Manifest: Implementation Plan

**Status:** ✅ Implemented (PRs 1–6 complete — see IMPLEMENTATION-STATUS.md for details; PR 7/Step 8 Agent Spec bridge remains deferred/optional)
**Author:** (generated with Copilot, grounded in current `pyagent-blueprint` v0.2.4 source)
**Scope:** `packages/pyagent-blueprint` core + a `RuntimeAdapter` contract designed to be provably implementable by *any* agent SDK — LangGraph, AutoGen, CrewAI, Semantic Kernel, OpenAI Agents SDK, or a hand-rolled in-house runtime.

---

## 1. Evaluation of the Ask

The proposal is directionally correct. I verified the current coupling directly in the codebase:

| File | Hard import on PyAgent runtime | Problem |
|---|---|---|
| `compiler.py` | `from pyagent_patterns.base import Agent, MockLLM`<br>`from pyagent_patterns.registry import get_pattern_class` | Compiler produces a `RuntimeGraph` of `pyagent_patterns.Pattern` objects — **only PyAgent can execute a compiled blueprint** |
| `generator.py` | `from pyagent_patterns.registry import get_pattern_class, list_patterns` | Scaffolding logic is pattern-registry-specific |
| `validator.py` | `from pyagent_patterns.registry import list_patterns` | Even *static* validation depends on the PyAgent pattern registry |
| `pyproject.toml` | `pyagent-patterns`, `pyagent-router`, `pyagent-providers`, `pyagent-context` as **required** dependencies | Anyone who wants just YAML parsing must install 4 runtime packages |

So today, `pyagent-blueprint` is a compiler front-end permanently wired to one runtime, not a manifest.

**Correction from rev 1 of this plan, per your feedback:** rev 1 leaned on a single LangGraph adapter as "the" proof of pluggability. That's the wrong bar — a single adapter proves nothing except "we can also target LangGraph." A framework-agnostic contract has to be validated against SDKs that are *structurally different from each other*, not just different from PyAgent. This revision restructures the plan around that requirement.

---

## 1a. Plain English: What Language *Is* This, and How Close Is It to "Open Agent Spec"?

### What the blueprint language actually is

A `pyagent-blueprint` file is a **YAML document that describes a whole multi-agent *system***, not a single agent. Think of it like a `docker-compose.yml`, but for a team of LLM agents instead of a set of containers. Concretely, one file (verified against `schema/spec.py` and the fixtures in `tests/fixtures/`) has six moving parts:

1. **`metadata`** — name, version, description, owner. Just bookkeeping.
2. **`providers`** — named model bindings (`primary: gpt-4.1-mini`, `fallback: gpt-4.1-nano`) that agents reference by name instead of hardcoding a model string.
3. **`agents`** — a dict of named agents, each with a `prompt`, a `provider` reference, optional `guardrails`, and a `description`. This is the "who" — the individual LLM-backed workers.
4. **`workflows`** — a dict of named workflows, each picking a `pattern` (e.g. `pipeline`, `supervisor`) and wiring specific agents into that pattern's slots (e.g. `stages: {researcher: researcher, reviewer: reviewer}`, or `routes: {billing: billing, tech: tech}`). This is the "how they're organized" — today this compiles directly into `pyagent_patterns.Pattern` objects, which is the exact coupling this plan is trying to remove.
5. **`contracts`** — per-workflow input/output typing plus SLAs (`latency_p95_ms`, `cost_max_usd`). This is a promise about behavior, not implementation.
6. **`context` / `observability`** — memory/compression policy, tracing, cost budgets.

So in plain terms: **it's a declarative "org chart + wiring diagram + SLA" for a group of agents, expressed as YAML, validated by Pydantic, and (today) compiled straight into one specific runtime's objects.** It answers *"which agents exist, what do they say, which model do they use, and how are they connected"* — it does not (today) answer *"how do I discover this agent from outside my system"* or *"what does this agent look like to someone who's never seen my codebase."*

### What "Open Agent Spec" means here (I researched this — it's AGNTCY's OASF)

There isn't a single trademarked "Open Agent Spec," but the closest real, actively-developed standard with that name in spirit is **OASF — the Open Agentic Schema Framework**, an Apache-2.0 project under **AGNTCY** (an agentic-AI interoperability initiative backed by Cisco Outshift, now a Linux Foundation-adjacent project — see `github.com/agntcy/oasf` and the live schema browser at `schema.oasf.outshift.com`). It's explicitly modeled on OCSF (Open Cybersecurity Schema Framework) — same data-modeling philosophy, same tooling lineage.

OASF's core unit is the **`record`** object — one record describes **one agent** (not a system of agents), with these required/recommended fields:

| OASF `record` field | Required? | Purpose |
|---|---|---|
| `name`, `version`, `schema_version` | Required | Identity + which OASF version this record conforms to |
| `description` | Required | Human-readable summary |
| `authors`, `created_at` | Required | Provenance/ownership |
| `skills` | Required (enum, from a published taxonomy) | What the agent can *do* — drawn from a hierarchical taxonomy (e.g. `Language Understanding → Semantic Understanding → Named Entity Recognition`), so skills are comparable across completely unrelated agents built by different teams |
| `domains` | Recommended (enum) | What business/subject-matter domain the agent applies to |
| `locators` | Optional | Where to actually find/fetch/run this agent (a pointer to source, an image, an API endpoint, etc.) |
| `modules` | Recommended (enum, extensible) | Pluggable extra capability descriptions — this is OASF's extension mechanism |
| `annotations` | Optional | Free-form string→string metadata bag |

### The direct comparison

| | `pyagent-blueprint` | OASF `record` |
|---|---|---|
| **Unit of description** | An entire *system* of agents + how they're wired together (workflows/patterns) | A single agent, described in isolation |
| **Primary purpose** | Compile a runnable multi-agent workflow | Enable discovery, cataloging, and identification of an agent across systems |
| **"What can it do"** | Free-text `prompt` string — not machine-comparable | `skills` — a controlled, hierarchical, enum-based taxonomy, machine-comparable across vendors |
| **"Where do I run it"** | Not modeled — assumes it will be compiled+run in-process by whichever adapter is installed | `locators` — explicit, first-class field |
| **Model/provider binding** | First-class (`providers` block) | Not part of the core record; would live inside a `module` extension if at all |
| **Orchestration/workflow topology** | First-class (`workflows`, `pattern`, `contracts`, SLAs) | **Not modeled at all** — OASF describes agents, not multi-agent orchestration graphs |
| **Extensibility model** | Ad hoc (add a new Pydantic field) | Formal — `modules` is a first-class enum-driven extension point, and OASF explicitly supports "private schema extensions" served from your own schema server |
| **Versioning discipline** | `api_version: pyagent/v1` string, no formal immutability policy | Explicit: once an OASF schema version ships, it's immutable except non-breaking doc fixes; new fields/breaking changes always bump the version |
| **Governance** | Single-vendor (PyAgent) | Multi-org, Linux Foundation-adjacent (AGNTCY), same lineage as OCSF |

### Bottom line, in plain English

`pyagent-blueprint`'s YAML is **much richer for describing "how do these agents work together" and much thinner for describing "how would a stranger discover, identify, or compare this agent to another one."** OASF is close to the exact opposite: rich for discovery/identity/skill-comparison, and has **no concept of workflow, pattern, or multi-agent wiring at all** — an OASF record describes one agent's capabilities, not a pipeline of them.

**They're not competitors — they're complementary layers.** A realistic alignment path (this doesn't need to block the framework-agnostic adapter work in this plan, but is worth tracking separately):

1. **Gap — no skill taxonomy:** `agents.<name>.prompt` is free text; there's no way to say "this agent has skill X" in a way another system could parse or compare. *Fix:* add an optional `skills: [...]` field per agent, backed by OASF's published skill taxonomy (or a superset), non-breaking since it's additive.
2. **Gap — no locator/discovery concept:** nothing in the blueprint says where a compiled agent actually *runs* or how an external system would find it once deployed. *Fix:* an optional `locators` block per agent or per package (ties in naturally with the "Agent Unit" packaging work already planned in Section 6/Step 6 of this doc).
3. **Gap — no formal extension mechanism:** today, adding a new capability means adding a new Pydantic field to core schema files. OASF's `modules` pattern (name + version + arbitrary payload validated against its own schema) is a cleaner, less core-schema-invasive way to let third parties extend records. *Fix:* consider a generic `extensions: dict[str, Any]` escape hatch per agent/blueprint, schema-versioned independently.
4. **Gap — no immutability/versioning discipline:** `api_version: pyagent/v1` is just a string; nothing enforces that a "v1" blueprint from six months ago still validates the same way today. *Fix:* adopt OASF's explicit policy — once a schema version ships, no breaking changes to it, ever; new capabilities bump the version.
5. **Inverse gap (OASF's side, for awareness only — not our problem to fix):** OASF has no notion of a multi-agent workflow, pattern, or SLA/contract at all — if PyAgent ever wanted to *publish* blueprint-defined agents into an OASF-compatible catalog for cross-org discovery, each individual `agents.<name>` entry would map reasonably well to one OASF `record`, but the `workflows`/`contracts`/`pattern` layer that ties them together has no OASF equivalent to map onto — that layer would have to stay PyAgent-specific or become a `module` extension.

**Practical takeaway:** the `RuntimeAdapter` work in this plan and OASF alignment are orthogonal and can proceed independently — `RuntimeAdapter` is about *executing* a blueprint on any runtime; OASF alignment would be about making the *agents inside* a blueprint discoverable/comparable outside PyAgent entirely. If cross-org agent discovery becomes a real requirement later, the cleanest entry point is item 1 above (an additive, optional `skills` field per agent) since it's non-breaking and immediately gives every `pyagent-blueprint` agent an OASF-taxonomy-comparable capability description without touching the workflow/orchestration layer at all.

---

## 2. What "Framework-Agnostic" Actually Requires

Agent SDKs differ along axes that any adapter contract must accommodate — otherwise the contract is secretly shaped like whichever SDK we designed it against first:

| Axis | LangGraph | AutoGen | CrewAI | OpenAI Agents SDK | Raw function-calling loop |
|---|---|---|---|---|---|
| Execution model | Explicit graph (`StateGraph`) | Conversational turn-taking between agent objects | Role-based crew with sequential/hierarchical process | Agent handoffs via `Runner` | Manual `while` loop calling `chat.completions` |
| State passing | Shared typed state object | Message history | Task outputs chained | Context object + handoffs | Whatever the developer wires up |
| Async support | Yes (native) | Partial | Partial | Yes | Depends |
| Streaming | Yes | Varies | Varies | Yes | Depends |
| Tool/function calling | Node-level | Agent-level | Task-level | Native | Native |
| Built-in retries/guardrails | No (bring your own) | No | No | Partial | No |

**Consequence for the design:** the `RuntimeAdapter` contract must be defined at the *lowest common denominator* — "given a spec, produce something invocable, and invoke it, returning a normalized result" — and must **not** assume graph-shaped execution, shared mutable state, or any particular async/streaming model. Anything beyond that (streaming, native tool-calling passthrough, etc.) becomes an **optional capability** an adapter can declare, not a required method.

This reframes Step 1 from "design an interface" to "design an interface **and prove it against at least two structurally dissimilar SDKs plus a conformance test suite** before calling it stable."

---

## 3. Target Architecture

```
pyagent-blueprint (core, lean)                    <- pip install pyagent-blueprint
├── schema/              Pydantic models (BlueprintSpec) — zero runtime deps
├── loader.py             YAML/JSON → BlueprintSpec
├── validator.py          Static validation — schema-only, no pattern-registry import
├── differ.py              Semantic diff between two specs
├── renderer.py            Mermaid / Markdown generation
├── adapter.py   (NEW)     RuntimeAdapter ABC, Capability enum, AdapterRegistry
├── conformance.py (NEW)   Reusable pytest suite any adapter author runs against their adapter
├── contract.py  (NEW)     JSON Schema I/O contracts + validation
├── packaging.py (NEW)     AgentUnit packaging metadata (deps, runtime, version)
└── cli.py                 validate | simulate | visualize | diff | package | adapters (list/doctor)

Reference adapters (prove genericity — deliberately dissimilar to each other):
├── pyagent-blueprint[pyagent]        adapters/pyagent_adapter.py     (graph-of-patterns, our own runtime)
├── pyagent-blueprint-langgraph        LangGraphAdapter                (explicit typed-state graph)
└── pyagent-blueprint-simple-loop      SimpleLoopAdapter                (bare OpenAI-style function-calling
                                                                          loop, NO graph library at all —
                                                                          this is the adapter that proves
                                                                          the contract isn't graph-shaped)
```

Core principle: **`pyagent-blueprint` core has ZERO dependency on any agent-execution framework.** Only `pydantic`, `pyyaml`, `click`, `jsonschema`.

---

## 4. The Adapter Contract (Designed for Structural Diversity)

```python
# src/pyagent_blueprint/adapter.py
from abc import ABC, abstractmethod
from enum import Flag, auto
from typing import Any, AsyncIterator
from pyagent_blueprint.schema.spec import BlueprintSpec


class Capability(Flag):
    """Optional features an adapter may or may not support.
    Core only ever requires COMPILE + RUN. Everything else is
    negotiated at runtime so the contract never assumes a graph,
    async streaming, or native tool-calling exists."""

    NONE = 0
    STREAMING = auto()
    NATIVE_TOOL_CALLING = auto()
    SYNC_EXECUTION = auto()  # some SDKs are sync-only
    PARTIAL_WORKFLOW_RUN = auto()  # can run a subset of a workflow (for debugging)


class RuntimeAdapter(ABC):
    """Compiles a framework-agnostic BlueprintSpec into a runnable object
    native to a specific agent framework, and executes it.

    Deliberately minimal: only `compile` and `run` are required. This is
    the lowest common denominator across graph-based (LangGraph), turn-based
    (AutoGen), role-based (CrewAI), and hand-rolled loop runtimes.
    """

    name: str
    capabilities: Capability = Capability.NONE

    @abstractmethod
    def compile(self, spec: BlueprintSpec) -> Any:
        """Return an opaque, framework-native compiled object.
        pyagent-blueprint core never inspects this object's internals —
        that's the whole point of the abstraction boundary."""

    @abstractmethod
    async def run(
        self, compiled: Any, workflow: str, input_: str, **kwargs: Any
    ) -> "AdapterResult":
        """Execute a compiled workflow. Adapters that are natively sync
        (Capability.SYNC_EXECUTION) wrap their own sync call internally —
        callers of RuntimeAdapter always await, even for sync-native SDKs."""

    # -- Optional capability-gated methods (default NotImplementedError) --

    async def stream(
        self, compiled: Any, workflow: str, input_: str, **kwargs: Any
    ) -> AsyncIterator[Any]:
        raise NotImplementedError(f"{self.name} does not declare Capability.STREAMING")

    def supported_patterns(self) -> list[str]:
        """Pattern/topology vocabulary this adapter understands, for
        validator.py's optional pattern-existence check. Adapters that
        don't have a fixed pattern vocabulary (e.g. a loop-based adapter)
        return an empty list — validator treats that as 'no constraint',
        not an error."""
        return []


class AdapterResult:
    """Normalized result envelope — every adapter must map its native
    return shape into this, so callers never branch on adapter identity."""

    def __init__(self, output: Any, raw: Any = None, usage: dict | None = None):
        self.output = output  # the primary answer, always present
        self.raw = raw  # adapter-native object, for advanced users
        self.usage = usage or {}  # tokens/cost if the adapter can report it


class AdapterRegistry:
    """Discovers adapters via Python entry-points — core never imports
    any adapter package directly."""

    GROUP = "pyagent_blueprint.adapters"

    @staticmethod
    def discover() -> dict[str, type[RuntimeAdapter]]: ...

    @staticmethod
    def get(name: str) -> type[RuntimeAdapter]: ...
```

Key design choices that make this genuinely framework-agnostic rather than LangGraph-shaped:

1. **`compile()` returns `Any`, opaque to core.** Core never assumes a graph, a node list, or typed state — it only knows "compile gives me something `run()` can use."
2. **`run()` is always async from the caller's perspective**, even though some SDKs (many CrewAI/AutoGen call sites) are sync-native — the adapter is responsible for wrapping its own sync call (e.g. `asyncio.to_thread`), not the caller.
3. **Streaming, native tool-calling, partial-workflow execution are `Capability` flags**, not required methods — an adapter that can't stream simply doesn't declare `STREAMING`, and callers check `adapter.capabilities & Capability.STREAMING` before calling `stream()`.
4. **`supported_patterns()` defaults to empty list, not required** — a loop-based adapter with no concept of named topology patterns isn't forced to invent one.
5. **`AdapterResult` is a normalized envelope** — this is what actually prevents caller code from special-casing "if adapter is LangGraph, read `.raw["messages"][-1]`" — every adapter must map its native output into `.output`.

---

## 5. Conformance Test Suite (this is what actually proves genericity)

New file: `src/pyagent_blueprint/conformance.py` — a reusable, importable pytest suite (parametrized fixture-based, not a script) that **any adapter author, inside or outside this repo, can run against their own adapter** to get objective pass/fail on contract compliance:

```python
# Usage from a third-party adapter package's own test suite:
from pyagent_blueprint.conformance import AdapterConformanceSuite


class TestMyAdapterConformance(AdapterConformanceSuite):
    @pytest.fixture
    def adapter(self):
        return MyCustomAdapter()
```

The suite checks, against a small set of canonical fixture blueprints (reused from existing `tests/fixtures/research_agent.yaml`, `customer_support.yaml`, plus new minimal single-agent and multi-agent-sequential fixtures):

- `compile()` doesn't raise on all canonical fixtures
- `run()` returns an `AdapterResult` (not a raw framework object)
- `run()` on an unresolvable workflow name raises a documented, catchable error (not an AttributeError from internals leaking through)
- If `Capability.STREAMING` is declared, `stream()` yields at least one chunk and the concatenation is consistent with `run()`'s `.output`
- If `Capability.SYNC_EXECUTION` is declared, `run()` still returns an awaitable
- Multiple sequential `run()` calls on the same `compiled` object don't leak state between calls (isolation check — this is the kind of bug class that's easy to introduce in stateful graph-based adapters and easy to miss in turn-based ones)

**This conformance suite, not a second reference adapter, is the actual deliverable that proves "framework-agnostic."** A single extra adapter only proves the interface fits one more shape; a conformance suite proves the interface's *contract* is checkable and enforceable independent of which SDK someone plugs in.

---

## 6. Reference Adapters — Chosen for Structural Dissimilarity, Not Popularity

To stress-test the contract, build (or design-review, if resourcing is tight) reference adapters that are **maximally different from each other**, not "LangGraph + one more graph-based thing." Expanding beyond the original two:

| Adapter | Execution shape | Why it's a good stress test |
|---|---|---|
| `pyagent_adapter` (ours) | Composed `Pattern` objects, our own DAG-like abstraction | Baseline — proves the contract works for the runtime it was extracted from |
| `SimpleLoopAdapter` | Bare `while` loop, manual OpenAI-style function-calling, **no framework, no graph library at all** | Cheapest way to disprove "the interface secretly requires a DAG." Zero external dependency — can run in CI unconditionally |
| `StateMachineAdapter` | Explicit finite-state-machine (`transitions`-style: states + triggers), no LLM-orchestration library | Proves the contract works when "workflow" means state transitions, not a message/graph pipeline — a different mental model than both of the above |
| `SequentialChainAdapter` | Strict linear pipeline — output of agent N is verbatim input to agent N+1, no branching, no shared state object at all | Proves the contract doesn't assume branching/routing exists; the minimal possible topology |
| `SingleAgentAdapter` | No orchestration whatsoever — one LLM call, one response, no workflow concept beyond "run this one agent" | The degenerate case. If the contract can't cleanly express "there is no graph, just an agent," it's over-designed for orchestration and under-designed for the simple 80% use case |
| `LangGraphAdapter` (community, external) | Explicit typed shared-state graph | Real-world, widely-adopted graph model, structurally different from our own Pattern composition |
| `AutoGenAdapter` (community, external) | Conversational turn-taking between agent objects, no explicit graph at all | Proves the contract survives a fundamentally different paradigm (conversation, not graph) — the biggest structural gap from LangGraph |
| `CrewAIAdapter` (community, external) | Role-based "crew" with sequential or hierarchical process manager; agents have roles/goals/backstories, tasks are assigned not routed | Proves the contract survives a *role-and-task* mental model rather than graph-nodes or conversation-turns — closer to an org chart than a DAG |
| `OpenAIAgentsSDKAdapter` (community, external) | `Runner` + explicit agent **handoffs**; native tool-calling and structured-output baked into the SDK itself | Stress-tests `Capability.NATIVE_TOOL_CALLING` for real (the other adapters mostly leave it undeclared); also the adapter most likely to expose whether our `contracts:` (input/output schema) block maps cleanly onto an SDK that already has its own native structured-output mechanism |
| `SemanticKernelAdapter` (community, external) | `KernelProcessStep` / plugin-based composition — "process" as a first-class stateful object with named steps and events, closer to an actor/event model than a DAG or conversation | Proves the contract survives an event-driven step model, plus tests interop with Kernel's own plugin/skill system, which is a different "tool-calling" surface than the others |

**Minimum bar before declaring the contract stable:** the conformance suite (Section 5) must pass against at least the first five (all in-house, zero/low external dependency) — these five alone span DAG, loop, state-machine, linear-chain, and no-orchestration-at-all shapes, which is a meaningfully broader test than "two adapters." The five external-SDK adapters (LangGraph, AutoGen, CrewAI, OpenAI Agents SDK, Semantic Kernel) are valuable as real-world validation and as the strongest possible "any SDK" proof point, but shouldn't gate the contract going stable, since they depend on external SDK release cadence and API stability outside our control.

---

## 6a. Where Should These Reference Adapters Live? In-Repo vs. pyagent.org Examples

This matters because it determines who maintains them, what breaks CI, and what signals "supported" vs. "illustrative."

**Recommendation: split by role, not by adapter.**

| Adapter | Recommended home | Why |
|---|---|---|
| `SimpleLoopAdapter`, `StateMachineAdapter`, `SequentialChainAdapter`, `SingleAgentAdapter` | **In-repo**, inside `packages/pyagent-blueprint/src/pyagent_blueprint/adapters/reference/` (or a small internal-only `pyagent-blueprint-testkit` sub-package) | These have **zero or stdlib-only dependencies**, run in every CI job on every commit, and their entire purpose is to be the conformance suite's regression fixtures. If they live outside the repo (e.g., only as docs on pyagent.org), the conformance suite loses its automatic, always-on CI enforcement — exactly the thing that makes "framework-agnostic" a tested claim instead of an assertion. They are test infrastructure first, examples second. |
| `LangGraphAdapter`, `AutoGenAdapter`, `CrewAIAdapter`, `OpenAIAgentsSDKAdapter`, `SemanticKernelAdapter`, and any other adapter with a real third-party SDK dependency | **pyagent.org as documented example implementations**, each its own separately-versioned package (`pyagent-blueprint-langgraph`, `pyagent-blueprint-crewai`, etc.), each with its own repo or its own subfolder outside the core package's dependency graph | These depend on external SDKs with independent, sometimes fast-moving release cadences (LangGraph ships fast; AutoGen has had breaking renames; Semantic Kernel's Python API has had multiple structural revisions; OpenAI's Agents SDK is comparatively new and still evolving). Pinning any of them into the core repo's CI means core CI breaks whenever one of five unrelated external SDKs ships a breaking change. Publishing them as docs-site example implementations (each with its own lightweight CI, own versioning, own "last verified against crewai==X.Y") keeps that churn fully isolated per-SDK. It also **demonstrates the real developer experience** — "here's what it looks like when someone outside the PyAgent team builds an adapter using only the public contract + conformance suite" — for five genuinely different, popular frameworks, which is the strongest possible proof of "usable by any SDK," stronger than any single in-house adapter could be. |

**Consequence for the plan:** Section 7 Step 4 splits into two sub-steps:
- **Step 4a** (in-repo, blocking, part of the "contract is stable" bar): `SimpleLoopAdapter` + `StateMachineAdapter` + `SequentialChainAdapter` + `SingleAgentAdapter`, all running through the conformance suite in core CI.
- **Step 4b** (pyagent.org, non-blocking, can ship incrementally / iterate independently): `LangGraphAdapter`, `AutoGenAdapter`, `CrewAIAdapter`, `OpenAIAgentsSDKAdapter`, `SemanticKernelAdapter` as documented example packages, each self-certifying against the published conformance suite (`pip install pyagent-blueprint` + run `AdapterConformanceSuite` in their own CI) rather than living in this repo's test matrix. These five don't need to ship together — recommend prioritizing by ecosystem reach: **LangGraph → OpenAI Agents SDK → CrewAI → Semantic Kernel → AutoGen**, based on current adoption signal, but any order is viable since they're fully independent of each other and of core.

This also directly serves the "pluggable unit usable by any SDK" goal from your original ask: the pyagent.org examples become the literal proof-by-demonstration that third parties — not just us — can build a conformant adapter, using nothing but the published `RuntimeAdapter` contract and conformance suite as their spec, across five of the most-adopted agent frameworks in the ecosystem.

---

## 7. Step-by-Step Plan (revised sequencing)

### Step 0 — Baseline safety net
- Freeze existing test suite as regression baseline (already present: `test_compiler.py`, `test_validator.py`, `test_cli.py`, `test_wire_integration.py`).
- Add `test_no_runtime_imports.py`: fails CI if `pyagent_patterns`/`pyagent_router`/`pyagent_providers`/`pyagent_context` is imported anywhere in core except inside `adapters/`.

### Step 1 — Define the generic `RuntimeAdapter` contract + `Capability` flags
- As specified in Section 4. Reviewed explicitly for graph/async/sync bias before implementation — no method may assume graph topology, shared mutable state, or async-native execution.

### Step 2 — Build the conformance suite FIRST, before any adapter
- Write `conformance.py` against the *interface only* (mock adapter implementations), before extracting our own compiler. This forces the contract to be testable independent of any real SDK, and catches interface design flaws before they're baked into a real adapter's assumptions.

### Step 3 — Extract our own compiler into `adapters/pyagent_adapter.py`, run it through the conformance suite
- Move current `compiler.py` logic there. Run `AdapterConformanceSuite` against it — this is the first real signal on whether the contract holds up.
- Move `pyagent-patterns`/`router`/`providers`/`context` to `[project.optional-dependencies] pyagent = [...]`.
- Deprecated shim: old `from pyagent_blueprint.compiler import BlueprintCompiler` still works, emits `DeprecationWarning`, delegates to the adapter.

### Step 4a — Build the in-repo reference adapters (the genericity proof, CI-blocking)
- `SimpleLoopAdapter`, `StateMachineAdapter`, `SequentialChainAdapter`, `SingleAgentAdapter` — all zero/stdlib-only dependency, all living in `adapters/reference/` inside core.
- Run the conformance suite against all four plus `pyagent_adapter` (five total, five different execution shapes) in CI on every commit.
- If the suite passes cleanly across all five without modifying the contract, that's the actual evidence the interface is framework-agnostic — not an assertion, a test result.
- If it *doesn't* pass cleanly for one of them, that's the signal to go back and fix the contract in Step 1 before anyone builds a LangGraph/CrewAI/Semantic Kernel adapter against a flawed interface.

### Step 4b — Publish community example adapters on pyagent.org (non-blocking, external SDK dependency)
- `LangGraphAdapter`, `AutoGenAdapter`, `CrewAIAdapter`, `OpenAIAgentsSDKAdapter`, `SemanticKernelAdapter` — each its own separately-versioned package/repo, each self-certifying via `pip install pyagent-blueprint` + the published conformance suite in their own CI (not this repo's CI).
- These are documented as example implementations on pyagent.org, not shipped inside `packages/`, so external SDK breaking changes never block or destabilize core CI.
- Their existence is proof-by-demonstration for third parties: "here's what a conformant adapter looks like, built by someone using only the public contract."

### Step 5 — Decouple `validator.py` / `generator.py` from the hard pattern-registry import
- `validator.py`'s only runtime dependency is `list_patterns()`. Replace with `adapter.supported_patterns()` (empty list if no adapter installed or adapter declares none) — validation degrades gracefully rather than failing to import.
- `generator.py` becomes adapter-aware the same way, with a `--adapter` CLI flag; without one installed, still scaffolds the generic schema skeleton.

### Step 6 — Packaging metadata → "Agent Unit"
- Extend YAML schema (new optional, backward-compatible top-level `package:` block): `name`, `version`, `author`, `runtime` (adapter name), `dependencies`.
- New `packaging.py`: `AgentUnitMetadata` model + validation that `runtime:` matches a discoverable adapter.
- New CLI command: `pyagent-blueprint package <path> -o dist/`.

### Step 7 — Publish community adapter template + docs
- `pyagent-blueprint adapter-template` CLI scaffold command: generates a starter adapter package (pyproject.toml with the entry-point pre-wired, a stub `RuntimeAdapter` subclass, and the conformance suite already imported into its test file) — lowers the bar for a third-party (LangGraph, AutoGen, CrewAI, Semantic Kernel, whoever) to build one.
- README gets the install matrix and "How to write your own adapter" section, linking the conformance suite as the acceptance bar.

### Step 8 (deferred, optional) — Agent Spec / ADP interoperability bridge
- Explicit export/import CLI flag (`--format agentspec`), not schema default — the external standard is still evolving; don't block this plan on it.

---

## 8. What Changes vs. What Stays the Same

| Stays the same | Changes |
|---|---|
| YAML schema for `agents`, `workflows`, `providers`, `context`, `observability` (fully backward compatible) | `compiler.py` logic moves to `adapters/pyagent_adapter.py`, deprecated shim kept |
| `loader.py`, `renderer.py`, `differ.py` (already framework-agnostic — confirmed no runtime imports) | `pyagent-patterns/router/providers/context` become optional extras, not hard deps |
| Existing test fixtures (`research_agent.yaml`, `customer_support.yaml`) | `validator.py`/`generator.py` lose their hard `pyagent_patterns` import |
| CLI command names (`validate`, `compile`, `render`, `test`, `diff`, `generate`) | `compile`/`test`/`generate` gain `--adapter` flag; new `adapters list`/`adapter-template` commands |

---

## 9. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Building only one extra adapter (LangGraph) and calling the contract "proven" | Rejected in this revision — require the conformance suite to pass against **five structurally dissimilar in-repo adapters** (DAG, loop, state-machine, linear-chain, single-agent) before the contract is declared stable |
| Interface designed with hidden graph/async bias | Section 2's axis table used explicitly during Step 1 design review; conformance suite built (Step 2) before any real adapter, forcing interface-first thinking |
| External SDK breaking changes (LangGraph/AutoGen/CrewAI/OpenAI Agents SDK/Semantic Kernel) destabilizing core CI | Those adapters live on pyagent.org as separately-versioned example packages with their own CI, self-certifying against the published conformance suite — never installed in core CI (Section 6a) |
| Breaking existing direct importers of `BlueprintCompiler` | Deprecated re-export shim, `DeprecationWarning`, 2 minor versions grace period |
| `pyagent-all` meta-package assumes bundled blueprint+patterns | Update its `pyproject.toml` to depend on `pyagent-blueprint[pyagent]` extra explicitly |
| Scope creep | Ship Steps 0–3 as PR #1 (mechanical, zero behavior change), Step 4a (in-repo reference adapters + conformance validation) as PR #2 — this is the PR that actually proves the plan — Steps 5–7 as follow-ons, Step 4b (pyagent.org examples) and Step 8 as independent, non-blocking follow-ups |

---

## 10. Suggested PR Sequencing

1. **PR 1** — Steps 0–3: contract, conformance suite (against mocks), extract our own adapter, run it through the suite. *Zero behavior change for existing users.*
2. **PR 2** — Step 4a: `SimpleLoopAdapter` + `StateMachineAdapter` + `SequentialChainAdapter` + `SingleAgentAdapter`, conformance suite run against all five in-repo adapters in core CI. **This is the PR that proves genericity — prioritize it over any specific third-party SDK adapter.**
3. **PR 3** — Step 5: decouple validator/generator from hard pattern-registry import.
4. **PR 4** — Step 6: packaging metadata + `pyagent-blueprint package` CLI.
5. **PR 5** — Step 7: adapter template scaffold + docs (published on pyagent.org).
6. **PR 6 (independent, non-blocking, can start anytime after PR 2)** — Step 4b: LangGraph, AutoGen, CrewAI, OpenAI Agents SDK, and Semantic Kernel example adapters published as pyagent.org docs-site packages, self-certified via the conformance suite in their own CI. Ship in any order (no interdependency), but prioritize by ecosystem reach: LangGraph → OpenAI Agents SDK → CrewAI → Semantic Kernel → AutoGen.
7. **PR 7 (deferred)** — Step 8: Agent Spec bridge.

---

## 11. Open Questions for You

1. Confirming the in-repo vs. pyagent.org split from Section 6a: zero/stdlib-dependency reference adapters (`SimpleLoopAdapter`, `StateMachineAdapter`, `SequentialChainAdapter`, `SingleAgentAdapter`) in-repo and CI-blocking; external-SDK adapters (`LangGraphAdapter`, `AutoGenAdapter`, `CrewAIAdapter`, `OpenAIAgentsSDKAdapter`, `SemanticKernelAdapter`) as pyagent.org example packages, non-blocking. Does this match your intent, or would you rather keep everything in-repo regardless of dependency weight?
2. Do we want to require the conformance suite as the objective acceptance bar for merging *any* future adapter (including community-contributed ones), rather than manual review?
3. Version bump: breaking change for `pip install pyagent-blueprint` no longer pulling in the runtime automatically — ship as `0.3.0` with deprecation shims, or hold for `1.0.0`?

---

## 12. Comparison Against the "Oracle Agent Spec Gap-Closing" Plan

A second plan was proposed (external draft, referred to below as **"the OAS plan"**) that also targets `pyagent-blueprint`, but frames the problem differently: instead of "make our runtime pluggable," it asks "become the governance layer on top of **Oracle's Agent Spec** as the portable interchange format." Both plans are compatible and non-competing, but they solve different halves of the same problem, and the OAS plan surfaces several things this plan should adopt.

### 0. Important terminology correction first

**The OAS plan's "Open Agent Spec" is NOT the OASF I researched in Section 1a.** They are two unrelated projects that both use "open" + "agent" + "spec" in their names:

| | OASF (Section 1a of this doc) | Agent Spec / PyAgentSpec (the OAS plan's subject) |
|---|---|---|
| Backed by | AGNTCY (Cisco Outshift), modeled on OCSF | **Oracle** — `github.com/oracle/agent-spec`, reference runtime is Oracle's **WayFlow** |
| Core unit | One `record` = one agent, for cataloging/discovery | A **Component graph** (Agents + Flows, control-flow/data-flow edges) = an executable multi-agent system definition |
| Closest analog to our blueprint | Nothing — it's a catalog entry, not a workflow | **Very close** — Agent Spec's Flow + edges is directly comparable to our `workflows` + `pattern` + agent wiring |
| Verified via | `github.com/agntcy/oasf`, `schema.oasf.outshift.com` | `github.com/oracle/agent-spec`, `oracle.github.io/agent-spec`, arXiv:2510.04173 |

This matters a lot: **Agent Spec (Oracle's) is structurally much closer to `pyagent-blueprint` than OASF is** — both describe multi-agent workflows with typed components and edges, not just individual agent identity cards. The OAS plan's gap analysis is therefore the more directly actionable one of the two, and Section 1a's OASF alignment path (skills taxonomy, locators, `modules`) should be treated as a separate, lower-priority, discovery-oriented track — not conflated with Agent Spec alignment.

### 1. What the two plans are actually solving

| | This plan (`RuntimeAdapter`) | The OAS plan |
|---|---|---|
| **Core question** | "Can a compiled blueprint *run* on any agent SDK?" | "Should our blueprint *become* (a superset of) the industry's portable interchange format?" |
| **Mechanism** | One abstract `RuntimeAdapter` per target SDK, each written by us or the community | One IR + a compiler-backend abstraction, with a **single Agent Spec export/import backend** that reaches WayFlow, LangGraph, CrewAI, AutoGen, MS Agent Framework, and OpenAI Agents *transitively*, via Agent Spec's own existing adapters |
| **Effort to reach N frameworks** | O(N) — one adapter per SDK, each hand-written and conformance-tested | O(1) for the frameworks Agent Spec already adapts to (Phase 3), plus O(1) direct backends only for the 2–3 highest-demand targets where governance features must survive (Phase 4) |
| **What's being proven** | The interface itself isn't graph/async/sync-biased (proven via 5 structurally dissimilar in-repo adapters + conformance suite) | That pyagent's *existing* governance features (routing, budgets, memory, guardrails, recovery, HITL) have no native home in Agent Spec, and can be carried across as `x-pyagent:*` extensions or direct-backend translations |
| **Gap catalog scope** | Narrow — OASF gaps only (skills, locators, extension mechanism, versioning discipline) | Broad — 10 gaps (G1–G10) mapped directly to existing pyagent features: provider routing, cost/SLA governance, memory tiers, pattern vocabulary, lifecycle tooling, HITL, guardrails, recovery policy, round-trip fidelity, language-neutrality |

### 2. What this plan should adopt from the OAS plan

1. **The "adopt, extend, never fork" principle (OAS Design Principle 1) is missing here and should be added.** This plan defines `RuntimeAdapter` in a vacuum; it never asks "does LangGraph/Agent Spec/CrewAI already have a concept for this, that we should map onto instead of reinventing?" Section 1.1 of the OAS plan ("what Agent Spec does well — do not rebuild") is a discipline this plan lacks entirely, and it's cheap to add: before finalizing `Capability` flags and `AdapterResult` shape, check them against Agent Spec's own Tracing/Component/LLM-config model for naming and structural alignment, so exporting to Agent Spec later (if ever pursued) isn't a second redesign.
2. **A single typed IR, decoupled from the Pydantic schema (OAS Phase 1) is a real gap in this plan.** Today, this plan has `BlueprintSpec` (the Pydantic schema) flow directly into `RuntimeAdapter.compile()`. The OAS plan's `pyagent_blueprint.ir` — a separate, runtime-independent representation that the schema *loads into* and that diff/render/test/compile all consume uniformly — is a better layering. **Recommendation: adopt this.** It costs little now (blueprint is small) and pays off the moment we want a second consumer of the same normalized structure (e.g. an Agent Spec exporter, a Mermaid renderer, a semantic differ) that shouldn't each re-parse or re-interpret raw Pydantic models slightly differently.
3. **Capability manifests with structured diagnostics, not just a `Capability` Flag enum.** This plan's `Capability` flags (Section 4) tell a caller *whether* a feature exists but not *why* something was dropped when compiling. The OAS plan's `CompileDiagnostic` / `explain_unsupported(ir)` concept (Phase 2) is strictly more useful for debugging a lossy compile, e.g., "your `contracts.sla.cost_max_usd` was dropped because `SimpleLoopAdapter` has no budget-enforcement hook." **Recommendation: extend `AdapterResult`/the adapter contract with an optional `compile_diagnostics: list[CompileDiagnostic]` returned alongside the compiled object**, so unsupported features are surfaced, not silently ignored — this directly closes this plan's own quiet gap around "what happens when an adapter can't honor part of a spec."
4. **The reserved extension namespace pattern (`x-pyagent:*`) is a concrete, exportable idea this plan has no equivalent for.** If/when this plan's `RuntimeAdapter` roster grows to include an Agent Spec backend (currently deferred to Section 7 Step 8 as "optional, out of scope"), the OAS plan's mapping table (Section 3 of the OAS plan) — direct mappings where Agent Spec has a concept, `x-pyagent:` extensions where it doesn't (routing, budgets, guardrails, recovery, HITL) — is a ready-made blueprint for that step. **Recommendation: when Step 8 is eventually picked up, adopt the OAS plan's Phase 3 mapping table wholesale rather than re-deriving it.**
5. **The 10-item gap catalog (G1–G10) is a stronger due-diligence artifact than this plan's Section 1a gap list**, because it's grounded in what pyagent *already has* (providers/router, contracts/observability, ContextLedger, 18 named patterns, BlueprintDiffer/Tester, Human-in-the-Loop pattern, guardrails guide, recovery config) rather than only in what an external record schema is missing. **Recommendation: fold G1–G10 into this plan's own risk/scope inventory** (Section 9) as "features that would need explicit handling if/when an Agent Spec backend is built" — even without committing to Phase 3–6 of the OAS plan now, this stops those features from being silently lost if an Agent Spec adapter is written later by someone unfamiliar with pyagent's fuller feature set.
6. **Round-trip fidelity / conformance profiles (G9) is a real blind spot in this plan.** This plan's conformance suite (Section 5) proves an adapter's `compile()`/`run()` behave correctly — it does **not** prove that going spec → adapter A → back to spec (or spec → Agent Spec → back) preserves meaning. If interop with any external format is ever pursued, "does a round trip lose information silently, or does it say so" is exactly the kind of test this plan's conformance suite should be extended to include, per-adapter, once any bidirectional (import *and* export) adapter exists — none of the current roster (Section 6) round-trips today, so this isn't urgent, but it should be a named future conformance-suite extension point, not an afterthought.

### 3. What the OAS plan should adopt from this plan (in case you also want to give that feedback)

1. **No structural-diversity discipline in interface design.** The OAS plan's `CompilerBackend` protocol is designed once and validated via a "regression suite from Phase 0 audit" — i.e., against our own existing behavior, not against SDKs chosen specifically because they're structurally *unlike each other*. This plan's Section 2 axis table (forcing the interface to the lowest common denominator across graph/turn/role/handoff execution models, sync vs. async, state-passing style) is a sharper methodology for catching a hidden bias *before* committing to an interface — the OAS plan should do this same exercise for its `CompilerBackend.compile()`/`.capabilities()` shape before Phase 2 locks it in.
2. **No zero-dependency, CI-blocking proof set.** The OAS plan's Phase 3/4 backends (Agent Spec, LangGraph, OpenAI Agents/AutoGen) all carry real external dependencies and, per its own risk list, "Agent Spec is a moving target" — there's no equivalent of this plan's Section 6a in-repo/pyagent.org hosting split, so it's not clear what in the OAS plan's sequencing actually runs in core CI on every commit versus what's allowed to be flaky/external. **Recommendation to that plan: adopt this plan's Section 6a split** — keep a small set of zero-dependency backends (their own version of `SimpleLoopAdapter`/`StateMachineAdapter`) in-repo as the CI-blocking genericity proof, and treat the Agent Spec/LangGraph/CrewAI backends as non-blocking, externally-versioned, self-certifying packages.
3. **No explicit "degenerate case" test.** This plan's `SingleAgentAdapter` (Section 6) — "no orchestration whatsoever, does the contract still work for the simplest possible case" — has no OAS-plan equivalent; all of its named patterns and backends assume some orchestration exists. Worth adding as a conformance check: does a trivial single-agent, no-Flow blueprint still compile and run through every backend without needing a degenerate one-node Flow to be constructed?

### 4. Bottom-line recommendation

Keep this plan's scope as-is for now (`RuntimeAdapter`, conformance suite, 5+5 adapter roster, in-repo/pyagent.org split) — it's the right, narrowly-scoped fix for the literal coupling problem described in Section 1. But before finalizing the adapter contract (Section 4) and calling it "done," make three small additions informed by the OAS plan, since they're cheap now and expensive to retrofit later:

- **Adopt the IR layering** (item 2 above) — have `loader.py` produce a small `BlueprintIR`, and have `RuntimeAdapter.compile()` take the IR, not the raw Pydantic `BlueprintSpec`, so a future Agent Spec exporter or semantic differ has one normalized thing to consume, not two.
- **Add `compile_diagnostics` to the adapter contract** (item 3 above) — even with only in-house adapters today, this makes "which parts of my blueprint did this adapter actually honor" answerable immediately, and it's the exact mechanism needed later if an Agent Spec backend is ever built.
- **Fold G1–G10 into Section 9's risk table** (item 5 above) as a forward-looking note, without committing to building any of Phases 3–6 of the OAS plan right now — this costs a paragraph and prevents an uninformed future contributor from writing a lossy Agent Spec adapter that silently drops routing/budgets/memory/guardrails.

Everything else in the OAS plan (Phases 3–6: Agent Spec interop backend, direct LangGraph/OpenAI backends, upstreaming extensions, full lifecycle tooling) is a **legitimate, larger, separate initiative** — it assumes this plan's Phase 0/1 (contract + conformance suite + decoupling) is already done, and should be scoped as a follow-on proposal once this plan's PR 1–2 (Section 10) ship, not merged into this plan's sequencing.


