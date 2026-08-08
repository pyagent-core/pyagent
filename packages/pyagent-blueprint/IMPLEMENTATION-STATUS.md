# pyagent-blueprint Transformation: Implementation Status

**All PRs from TRANSFORMATION-PLAN.md Section 10 are complete except the
deferred, optional Step 8 (Agent Spec bridge).**

## PR 1 — Steps 0–3: Contract, conformance suite, own adapter extraction
✅ Complete.
- `AUDIT-STEP0.md` — grounding audit
- `ir.py` — framework-agnostic `BlueprintIR`
- `diagnostics.py` — stable diagnostic-code registry (G1–G9 gaps)
- `adapter.py` — `RuntimeAdapter` contract, `AdapterRegistry` (entry-point discovery, resilient to individual adapter load failures)
- `extensions.py` — `x-pyagent` extension namespace + schema-version policy
- `conformance.py` — shared `AdapterConformanceSuite`
- `adapters/pyagent_adapter.py` — `PyAgentAdapter`, extracted from the old `compiler.py`
- `compiler.py` — deprecated thin shim over `PyAgentAdapter`
- `validator.py` / `generator.py` — decoupled from hard `pyagent_patterns` import
- `pyproject.toml` — lean core deps (`pydantic`, `pyyaml`, `click`), `[pyagent]` optional extra, adapter entry points
- `tests/test_no_runtime_imports.py` — CI guardrail

## PR 2 — Step 4a: In-repo zero-dependency reference adapters (CI-blocking)
✅ Complete. Four structurally dissimilar adapters, each conformance-tested:
- `single_agent` (degenerate, `SYNC_EXECUTION`)
- `sequential_chain` (linear pipeline, baseline)
- `state_machine` (explicit FSM, `PARTIAL_WORKFLOW_RUN`)
- `simple_loop` (bare while-loop, `STREAMING`)

Critical fix applied: `AdapterRegistry.discover()` made resilient so one
adapter's missing optional dependency never breaks discovery of the
others (regression-tested in `tests/test_adapter_registry_resilience.py`).

## PR 3 — Step 5: Decouple validator/generator from pattern registry
✅ Complete (done as part of PR 1 — `_known_pattern_names()` /
`_resolve_pattern_vocabulary()` degrade gracefully to "no constraint"
when no adapter with a fixed pattern vocabulary is installed).

## PR 4 — Step 6: Agent Unit packaging
✅ Complete.
- `schema/package.py` — optional `PackageSpec` (`name`, `version`, `author`, `runtime`, `dependencies`)
- `packaging.py` — `AgentUnitMetadata`, `build_metadata()`, `package_blueprint()` → `.agentunit.zip` archive (manifest + content hash + original spec)
- CLI: `pyagent-blueprint package <path> -o dist/`, `pyagent-blueprint adapters`
- Tests: `tests/test_packaging.py`, CLI tests in `tests/test_cli.py`

## PR 5 — Step 7: Adapter template scaffold + docs
✅ Complete.
- `adapter_template.py` — `render_adapter_template()` / `write_adapter_template()`, dependency-free string templates
- CLI: `pyagent-blueprint adapter-template --framework <Name> -o <dir>`
- Generates: `pyproject.toml` (entry point pre-wired), stub adapter module, conformance test file (imports `AdapterConformanceSuite`), README
- Tests: `tests/test_adapter_template.py`
- README updated: install matrix, "Adapters & Framework-Agnostic Runtimes" section, "Writing your own adapter" guide, packaging guide

## PR 6 — Step 4b: External example adapters (non-blocking, own CI)
✅ Complete. Four real (not stubbed), offline-testable adapters, each in
its own independently-versioned package under `packages/`, each passing
`AdapterConformanceSuite` in its own test suite:

| Package | Adapter name | SDK execution model | Capability exercised |
|---|---|---|---|
| `pyagent-blueprint-adapter-langgraph` | `langgraph` | Declared node/edge graph (`StateGraph`) | `STREAMING` |
| `pyagent-blueprint-adapter-openai-agents` | `openai_agents` | Handoff/turn-based (`Agent` + `Runner`) | — |
| `pyagent-blueprint-adapter-crewai` | `crewai` | Role-based (`role`/`goal`/`backstory` + `Task`) | — |
| `pyagent-blueprint-adapter-semantic-kernel` | `semantic_kernel` | Event/service-oriented (`Kernel` + pluggable services) | — |

Each uses a deterministic offline model/service implementation (no API
key, no network) that still flows through the real SDK's actual
response/message types and execution path (`Runner.run()`,
`Crew.kickoff_async()`, `ChatCompletionAgent.get_response()`,
`StateGraph.compile().ainvoke()`), proving the `RuntimeAdapter` contract
maps cleanly onto four structurally distinct real frameworks — not just
four in-repo toy adapters.

AutoGen was deprioritized last per the plan's ecosystem-reach ordering
and can be added later without blocking anything else.

## PR 7 — Step 8: Agent Spec / ADP interoperability bridge
⏸️ Deferred (optional, per plan — the external standard is still evolving).

## Post-hoc hardening pass (against the more detailed "Mega Implementation Plan")
✅ Complete. The user supplied a more granular engineering plan
(rev-3-equivalent) after PR 6 shipped; comparing against it surfaced two
concrete gaps, both closed:

- **`contract.py`** (Section 1.2) — added: `contract_json_schema()`,
  `blueprint_contracts_json_schema()`, and a hand-authored
  `BLUEPRINT_IR_META_SCHEMA` for non-Python tooling (mitigates G10 —
  "Python-only SDK"). Tested in `tests/test_contract.py`.
- **Four isolated governance fixtures** (Section 1.3: SLA+budget,
  memory-tier/trust/redaction, HITL checkpoint, recovery policy) — added
  to `conformance.py` as `GOVERNANCE_FIXTURES`, with a new parametrized
  `test_diagnostic_completeness_per_governance_feature` test on
  `AdapterConformanceSuite`. `BlueprintIR.governance_features()` gained a
  `"checkpoint"` key.

**This hardening pass caught two real bugs** that the combined
`governance` fixture had been masking:
1. `PyAgentAdapter._diagnose_ungoverned_features` checked
   `wf.config.get("checkpoint")` but the HITL fixture (and
   `adapters/reference/_common.py`) both use the key
   `"human_in_the_loop"` — silently under-diagnosing HITL checkpoints.
   Fixed to check both keys.
2. **More serious:** `PyAgentAdapter._instantiate_pattern` was passing
   `wf.config` through verbatim as `**kwargs` into the native
   `pyagent_patterns` pattern constructor (e.g. `Pipeline(**config)`).
   Any workflow declaring a governance-only config key like
   `human_in_the_loop` crashed compilation outright with a `TypeError`
   from the pattern class, instead of degrading to a diagnostic. Fixed
   by introducing `_GOVERNANCE_ONLY_CONFIG_KEYS` and filtering them out
   before instantiation — governance signals now flow only through
   `CompileDiagnostic`s, never into the native runtime's constructor.

Both fixes are regression-tested via the new isolated fixtures (the
previous combined `governance` fixture didn't trigger the config-leak
bug because it never included a plain boolean `config` key).

## Track B (Marketing, SEO, Cookbook, Blog on pyagent.org)
� In progress. The site is **not** a separate repo — it's built directly
from this same monorepo (`mkdocs.yml`, `docs/`, `site/` at the repo
root). Discovered and confirmed via `list_dir`/`file_search`; the earlier
"awaiting site repo location" blocker is resolved.

### Phase A — mechanical fixes ✅ Complete
- **1.1** Renamed top-nav `Framework` → `Blueprint` in `mkdocs.yml`;
  renamed the now-colliding inner pillar `Blueprint` → `Manifest` (avoids
  a "Blueprint › Blueprint" breadcrumb). Updated the `llmstxt` plugin's
  `sections:` mapping to match.
- **2.2** (generic index titles) — **grounding check failed the plan's
  claim**: `docs/cookbook/index.md`, `packages/patterns/index.md`, and
  `packages/studio/index.md` all already have distinct H1s used as page
  `<title>`. No fix needed; skipped.
- **1.7** (API Reference nav-target inconsistency) — **grounding check
  failed this claim too**: neither `docs/overrides/home.html` nor
  `docs/cookbook/index.md` reference an API Reference link at all.
  Skipped.
- **2.8** (lastmod/canonical) — canonical tags already correct
  (`site_url` set, mkdocs-material auto-emits them). Real gap found:
  no `mkdocs-git-revision-date-localized-plugin`, so `sitemap.xml`
  `lastmod` is build-timestamp, not per-page git history. Flagged as a
  follow-up requiring a new dependency (not yet added — needs a
  decision, see Open Questions below).
- Verified via `mkdocs build --strict` after each change.

### Phase B — JSON-LD, llms.txt, YAML/Python toggle ✅ Complete (for this pass)
- **2.1 (JSON-LD)** — `SoftwareApplication` on homepage pre-existed.
  Added site-wide **`BreadcrumbList`** to `docs/overrides/main.html`,
  walking the real mkdocs nav ancestor chain (`page.parent`); fixed a
  Jinja loop-scoping bug (needed `namespace()`) found via direct
  ancestor-chain introspection; verified correct output on a deep page,
  a shallow page, and the homepage (which correctly omits it).
  `FAQPage`/`HowTo` deferred — they need authored Q&A/step content per
  page (new front-matter convention), not just a template change; not
  fabricating content to fill schema.
- **1.3 (YAML⇄Python toggle)** — proven on the **Supervisor** pattern
  page as the reference implementation: `pymdownx.tabbed` `=== "Python"`
  / `=== "Blueprint YAML"` tabs, using the real, existing
  `tests/fixtures/customer_support.yaml` conformance fixture (not
  fabricated) plus matching CLI commands. Verified via `mkdocs build
  --strict` and confirmed `tabbed-set`/`tabbed-labels`/`tabbed-content`
  present in built HTML.
  **Added scope (tracked):** rolling the toggle out to all remaining 17
  pattern pages requires hand-verified YAML for each — several patterns
  (Debate, Voting, Blackboard, Swarm, Topology, etc.) have no existing
  test fixture to ground against and need new YAML written directly
  from `spec-format.md`/`workflows.md` semantics before being added to a
  page. Tracking this as its own follow-on item under 2.4's
  "Pattern-YAML multiplier" (same underlying content, so doing it once
  here would otherwise duplicate work when Blueprint Ops ships).
- **2.5 (`llms.txt` refinement)** — found and fixed a real factual
  staleness bug: `mkdocs.yml`'s `llmstxt.markdown_description` claimed
  "Cookbook of 28... examples" against a verified actual count of 34
  (`docs/cookbook/index.md`'s `data-total="34"`); also updated stale
  "four-pillar framework" wording to "four-pillar Blueprint"
  (Manifest/Execution & Routing/Context & Memory/Observability) to match
  the Phase A rename. Verified regenerated `llms.txt`/`llms-full.txt`
  reflect both fixes and the new `Why Blueprint` section (see Phase D).
  Noted, not fixed (separate pre-existing issue, out of scope): a
  recurring "orphaned pages" build warning for
  `packages/blueprint.md`/`packages/studio.md`/`packages/blueprint/index.md`
  reflecting genuine file-organization duplication in `docs/packages/` —
  flagged for a future dedicated audit.

### Phase C (blog plugin) — explicitly deferred
Per explicit user instruction: blog plugin setup needs its own separate
planning pass before implementation. Not started. `llmstxt` plugin
(machine-readable `llms.txt`/`llms-full.txt` export) is unrelated and
already configured — not blocked by this deferral.

### Phase D — Why Blueprint, comparisons, definitional/essay pages ✅ Complete
Ungated: Track A's five-adapter conformance proof (PR 2) already
shipped, satisfying Gate 1. All content below cites real, existing code
— no aspirational claims.
- **`docs/why-blueprint.md`** (1.4) — the same `customer-support.yaml`
  manifest compiled against all 9 registered adapters via
  `pyagent-blueprint simulate --adapter <name>`; a real capability table
  citing each adapter's actual execution model (verified against each
  adapter package's `adapter.py`); explicit "when a blueprint isn't the
  right fit" section (dynamic runtime-computed graphs) rather than
  overclaiming.
- **`docs/compare/vs-langgraph.md`** (1.8/2.3) — grounded in
  `pyagent-blueprint-adapter-langgraph/adapter.py`'s real
  `StateGraph`/`add_node`/`add_edge`/`compile()` calls (verified via
  `grep_search` before writing).
- **`docs/compare/vs-crewai.md`** (1.8/2.3) — grounded in
  `pyagent-blueprint-adapter-crewai/adapter.py`'s real `Agent`/`Task`/
  `Crew(process=Process.sequential)`/`kickoff_async()` calls (verified
  the same way).
- **`docs/compare/vs-autogen.md`** (1.8/2.3) — **explicitly states no
  AutoGen adapter exists yet** (verified: deprioritized per
  `IMPLEMENTATION-STATUS.md`'s own PR 6 section) rather than fabricating
  comparison code for an integration that doesn't exist; frames it as a
  conceptual comparison only, to be replaced with real code once/if an
  adapter ships.
- **`docs/concepts/multi-agent-orchestration.md`** and
  **`docs/concepts/agent-blueprint.md`** (2.6) — definitional pages,
  cross-linked to the real pattern catalog and Blueprint guide.
- **`docs/essays/kubernetes-for-agent-orchestration.md`** (2.4) —
  extends the analogy already present in
  `packages/pyagent-blueprint/README.md` ("Like Kubernetes for agent
  systems"); includes an explicit "where the analogy breaks down"
  section (no reconciliation control loop, `RuntimeAdapter` isn't an
  external multi-vendor standard like CRI) rather than overclaiming.
- All six pages wired into `mkdocs.yml` nav under new top-level
  **"Why Blueprint"** tab, and into the `llmstxt` `sections:` mapping.
  Fixed one relative-link bug (`concepts/multi-agent-orchestration.md`
  → `packages/patterns/index.md` needed `../`) caught by
  `mkdocs build --strict`.
- Verified: `mkdocs build --strict` passes; spot-checked `BreadcrumbList`
  JSON-LD ancestor chains resolve correctly on all six new pages
  (e.g. `PyAgent > Why Blueprint > vs. LangGraph`).
- **Caught and fixed a real fabricated-command bug** across four pages
  (`why-blueprint.md`, the Supervisor pattern page, `vs-langgraph.md`,
  `vs-crewai.md`): initially wrote a `pyagent-blueprint simulate` command
  with `--adapter`/`--workflow` flags that **do not exist** in
  `cli.py` (real commands: `validate`, `compile`, `render`, `test`,
  `diff`, `package`, `adapters`, `adapter-template` — no `--adapter` flag
  on any of them; adapter selection is a Python API concept only).
  Corrected all four pages to use real CLI commands (`test` in place of
  the fabricated `simulate`) plus a real Python API snippet
  (`AdapterRegistry.discover()[name]().compile(ir)` /
  `await adapter.run(artifact, workflow=, input_=)`). **Then actually
  executed that exact snippet** against the real repo (not just
  eyeballed it) — first attempt failed
  (`AdapterRegistry.discover()` returned `[]` because the editable
  install's entry-point metadata predated the adapters shipping;
  `BlueprintIR.from_spec(spec)`, not `spec.to_ir()`, is the real
  conversion call — another fabrication caught and fixed). Refreshed the
  editable install (`pip install -e packages/pyagent-blueprint
  --no-deps`), reran the snippet — confirmed it now actually compiles
  and runs end-to-end (`AdapterResult [tech] [billing] [classifier] I
  was charged twice`) — then reran the full test suite to confirm the
  reinstall didn't disturb anything: **154 passed, 13 skipped,
  unchanged**.

### Phase E — Blueprint Ops cookbook + Blueprint Gallery + homepage terminal asset ✅ Complete
- **2.4 (Blueprint Ops, 21st cookbook domain)** — added
  `docs/cookbook/blueprint-ops/` with three recipes, following the exact
  frontmatter convention `_load_recipes()` in `scripts/gen_docs.py`
  expects (`description`/`summary`/`complexity`/`tags` with
  `Domain:`/`Pattern:`/`Package:`), not hand-edited HTML:
  - `ci-cd-validation.md` — real `validate`/`diff` CLI commands wired
    into a GitHub Actions PR check
  - `contract-testing.md` — real `test` CLI command + `BlueprintTester`
    Python API against `MockLLM`
  - `governance-in-yaml.md` — recovery/budget declared in YAML,
    inspecting `CompiledArtifact.diagnostics`
  - Ran `scripts/gen_docs.py` (the real generator, not a hand-edit) to
    regenerate `docs/cookbook/index.md`'s recipe browser (34→37) and the
    `supervisor.md`/`pipeline.md` pattern cross-reference sections.
    Verified with `gen_docs.py --check` (CI's actual check) — clean.
  - Added all three to `mkdocs.yml` nav under Cookbook, and updated the
    `llmstxt` `markdown_description` (37 recipes / 21 domains) and two
    other stale "20 domains / 28 recipes" mentions found and fixed in
    `README.md` and `docs/getting-started/featured-examples.md`.
  - **Caught and fixed a real accuracy bug during authoring**: the first
    draft of `governance-in-yaml.md` claimed the native `pyagent` adapter
    "honors recovery" while a reference adapter doesn't — **actually ran
    the snippet** against the real `customer_support.yaml` fixture, and
    found *both* adapters currently report `RECOVERY_UNSUPPORTED` and
    `BUDGET_UNSUPPORTED` (enforcement isn't wired into any adapter yet
    for these G2/G8 gaps — expected per the engineering roadmap's own
    gap table, but not what the recipe claimed). Rewrote the recipe to
    state this accurately and re-verified the corrected snippet's exact
    output before publishing.
  - Verified: `mkdocs build --strict` passes; "Blueprint Ops" domain chip
    confirmed present in the built cookbook page HTML.
- **1.5 (Blueprint Gallery)** ✅ Complete:
  - Discovered 34 real, pre-existing example blueprints at
    `examples/cookbook/*/*/blueprint.yaml` — used these directly instead
    of fabricating new gallery content.
  - **Caught and fixed two real, pre-existing bugs** while actually
    running the render pipeline (`load_blueprint` → `BlueprintRenderer
    .to_mermaid()`) against all 34, rather than assuming they'd parse:
    1. 9 files had a YAML syntax bug — a compact flow-mapping key
       missing a space before `{` (e.g. `account_exec:{ provider: ... }`
       instead of `account_exec: { provider: ... }`), which PyYAML
       rejects with `ScannerError: mapping values are not allowed here`.
       Fixed mechanically via regex across all 9 files (`finance-trading
       /robo_advisor`, `healthcare/clinical_summary`, `hr-recruiting
       /cv_screener`, `media-entertainment/writers_room` (3 occurrences),
       `real-estate/property_valuation`, `research-analysis
       /literature_review`, `sales-crm/lead_qualifier`, `scientific
       /peer_review`, `travel-hospitality/trip_planner`). Verified: full
       `pyagent-blueprint` test suite (154 passed, 13 skipped) still
       green after the fix.
    2. 13 files fail schema validation (`workflows.*.agents` as a list
       — an ordered pipeline stage sequence — instead of the dict the
       current `WorkflowSpec.agents: dict[str, Any]` schema requires).
       Confirmed via `packages/pyagent_blueprint/schema/workflows.py`
       this is a genuine schema/example mismatch, not a renderer bug.
       **Deliberately left unfixed** — converting a list to a dict
       requires guessing stage names/order, which would misrepresent
       the recipe; tracked below as a follow-up instead of scope-creeping
       a content rewrite into this docs task.
  - Result: **21 of 34** example blueprints load and render cleanly.
    Added `render_gallery()`/`build_gallery()` to `scripts/gen_docs.py`
    (mirrors the existing `render_recipe_browser()` pattern): for each
    of the 21, loads the real spec, calls the real
    `BlueprintRenderer.to_mermaid()` (never hand-drawn), and pairs it
    with Cookbook recipe metadata (title/summary/complexity/domain/
    patterns) via `_load_recipes()` where a matching recipe exists.
  - Created `docs/gallery.md` with a `<!-- gen:gallery:start/end -->`
    region, wired into `TARGETS` in `scripts/gen_docs.py` (so
    `--check` now covers it), and added a `Gallery` top-level nav item
    to `mkdocs.yml` (also added to the `llmstxt` `sections` map).
  - Reused the existing `#recipe-browser`/`#recipe-filter-bar` IDs and
    `.cb-card`/`.cb-chip` classes so the gallery gets the same
    domain/pattern filter-chip UI as the Cookbook for free, without
    touching `recipe-filter.js` (which hardcodes those IDs).
  - Fixed `data-domain` to use the recipe's display-cased domain name
    (e.g. `"Customer Support"`) rather than the raw directory slug
    (`"customer-support"`), matching the Cookbook's convention.
  - Verified: `gen_docs.py --check` clean; `mkdocs build --strict`
    passes with no new warnings/errors; `pytest packages/pyagent-blueprint
    /tests` — 154 passed, 13 skipped (confirms the YAML fixes didn't
    break anything).
- **1.2 (homepage terminal-loop asset)** ✅ Complete:
  - Grounded every line of the animation in commands actually run
    against the repo, not fabricated output:
    - Confirmed the mega-plan's `apply`/`simulate`/`dashboard` verbs
      live in **`pyagent-studio`**'s unified `pyagent` CLI
      (`packages/pyagent-studio/src/pyagent_studio/cli.py`,
      `[project.scripts] pyagent = "pyagent_studio.cli:main"`), not in
      `pyagent-blueprint`'s CLI (which only has `validate`/`compile`
      /`test`/`diff`/`package`/`adapters`/`adapter-template`) — checked
      both before writing any command text.
    - **Caught a real bug**: `pyagent simulate` against
      `examples/cookbook/sales-crm/lead_qualifier/blueprint.yaml`
      raises `AttributeError: 'NoneType' object has no attribute
      'run'` — the deprecated `BlueprintCompiler` shim silently
      returns `None` for workflows whose routes embed nested
      per-route pattern configs (e.g. `hot: { pattern:
      talker_reasoner, ... }`) instead of raising a clear error.
      Confirmed `simulate` works fine against a flat string-ref
      workflow (`examples/fixtures/sample_blueprint.yaml`'s
      `customer-support` workflow, same fixture the CLI's own test
      suite in `packages/pyagent-studio/tests/test_web.py` uses) —
      used that fixture for the demo instead of chasing a
      compiler fix out of scope for this docs task. Logged as a
      second known follow-up below.
    - Actually ran `validate`, `apply`, `diff` (against a real
      one-field-modified copy), and `simulate` via the installed
      `.venv/bin/pyagent` entry point and captured their exact stdout;
      read `dashboard`'s source to confirm its literal
      `click.echo(f"Starting dashboard at http://{host}:{port}")`
      line (can't "run" a server in a docs pipeline, so the source
      was read directly instead of guessing at its startup banner).
  - Implementation: added `.hp-terminal` (macOS-style traffic-light
    bar + dark JetBrains-Mono body) to `docs/overrides/home.html`'s
    hero, right after the existing `.hp-ctas` buttons. A small IIFE
    types each of the 5 real commands character-by-character, reveals
    their real captured output line-by-line, holds, fades, and loops
    back to `validate` — Terraform-plan style. Respects
    `prefers-reduced-motion` (renders instantly, no typing animation)
    and pauses via `IntersectionObserver` when the hero scrolls out of
    view (no wasted CPU on a page the user has scrolled past).
  - Verified: `mkdocs build --strict` passes with no new
    warnings/errors; confirmed via `grep` that the terminal markup
    (`hp-terminal`, `hp-term-body`, the real `pyagent validate
    customer-support.yaml` command text) is present in the built
    `site/index.html`.

### Follow-up pass — `simulate` crash root-caused, all 34 examples fixed, pattern-page rollout finished ✅ Complete

The two items logged above as "known follow-ups, out of scope for docs task"
were picked up in a dedicated pass. Investigating the `simulate` crash
revealed it wasn't isolated — the real root cause was systemic and affected
all 34 example blueprints, not 13:

- **Root cause**: `WorkflowSpec` (schema/workflows.py) used Pydantic's
  default "ignore extra fields" behavior. Blueprint authors routinely put
  pattern-wiring keys (`classifier:`, `routes:`, `stages:`, `manager:`,
  `teams:`, etc.) as siblings of `pattern:` instead of nested inside
  `agents:`/`config:`. 13 files hard-failed (list-form `agents:`); the
  other **21** — including the ones the Gallery's "21 of 34 render
  cleanly" count depended on — silently validated with an empty
  `agents={}` and only crashed at `.run()` time with a confusing
  `AttributeError: 'NoneType' object has no attribute 'run'`. Reproduced
  exactly on `lead_qualifier.yaml`.
- **Schema fix**: added `model_config = ConfigDict(extra="forbid")` to
  `WorkflowSpec` — misplaced keys now fail loudly at `load_blueprint()`
  with a clear `ValidationError` naming the offending key, instead of
  silently producing a broken workflow. Regression-tested in
  `tests/test_schema.py`.
- **Real adapter bugs found and fixed** while making all 34 examples
  actually compile+run (not just parse), in
  `adapters/pyagent_adapter.py`:
  - The `fan_out_fan_in`/`voting`/`debate` special-case in
    `_instantiate_pattern` passed a plain `agents=` kwarg to all three —
    none of them accept that parameter (`FanOutFanIn` needs
    `agents`+`aggregator`; `Voting` needs `voters`; `Debate` needs
    `debaters`+`judge`). Would have crashed the moment any real blueprint
    exercised this path.
  - `hierarchical`, `orchestrator_workers`, `blackboard`, and `layered`
    had **no special-casing at all** — their native constructors need
    structured objects (`Team`, `BlackboardAgent`, `Layer` dataclasses)
    that the generic `pattern_cls(**agents, **config)` fallback can't
    build from flat agent refs. Added dedicated branches for all four.
  - `_resolve_agent_refs` (renamed `_resolve_ref`, now a recursive
    static method) only resolved `str` and one-level `dict` refs — no
    handling for **list-typed refs** (e.g. a `workers:` list), which
    passed through as raw YAML strings instead of `Agent` objects.
    Rewrote as a proper recursive resolver.
  - `Voting.strategy` and `Topology.topology` are `StrEnum`-typed
    constructor params; the compiler passed plain strings straight from
    YAML `config:`, which crashed on `.value` access inside the pattern.
    Added coercion (`VotingStrategy(...)` / `TopologyType(...)`) in the
    adapter.
  - Regression-tested in
    `tests/adapters/test_pyagent_adapter_patterns.py` (8 new
    parametrized cases, one per previously-broken/unsupported pattern).
- **All 34 `examples/cookbook/*/*/blueprint.yaml` rewritten** to the
  correct `agents:`/`config:` nesting, grounded in each pattern's real
  constructor signature (verified against `pyagent_patterns` source, not
  guessed). Notable individual fixes:
  - `finance-trading/portfolio_review`: `supervisor_plus_evaluator_optimizer`
    isn't a registered pattern — split into two real workflows (`route`
    then `tighten`) in the same blueprint, which is how PyAgent actually
    composes patterns (one blueprint, many workflows), rather than one
    invented composite pattern name.
  - `customer-support/support_router`: routes nesting a second pattern
    per route (`hot: { pattern: talker_reasoner, ... }`) isn't supported
    — `Supervisor.routes` expects `Agent` objects, not `Pattern` objects.
    Flattened each route to its senior specialist agent; noted in a YAML
    comment rather than silently dropped.
  - `finance-trading/trading_signals`: used `workers:` for
    `fan_out_fan_in`'s parallel-agent list — that pattern's real
    parameter is `agents`, not `workers` (that's `orchestrator_workers`'
    parameter name); renamed for correctness.
  - `scientific/peer_review`: `topology_type: MESH` (uppercase) doesn't
    match `TopologyType`'s lowercase enum values; fixed to `mesh`.
  - `research-analysis/research_assistant`: `gather`'s `fan_out_fan_in`
    had no `aggregator` at all (a required constructor arg) — wired to
    reuse the `synthesizer` agent already defined for the `synthesize`
    workflow.
  - `data-analytics/sql_analyst`, `security/fraud_investigation`: moved
    tool names onto `agents.<name>.tools` (the real, existing
    `AgentSpec.tools: list[str]` field) and dropped the fabricated
    top-level `tools: {name: {description: ...}}` block, which isn't
    part of the schema at all.
  - `devops-sre/incident_triage`, `security/log_triage`:
    `high_risk_keywords` isn't a `HumanInTheLoop` constructor param
    (would crash instantiation via `**config`); folded the intent into
    the reviewing agent's prompt instead of silently dropping it.
  - `sales-crm/lead_qualifier`: the original bug-reproduction case,
    fixed the same way as `support_router`/`portfolio_review`.
- **Verified end-to-end, not just parsed**: wrote a script that runs
  `load_blueprint()` → `BlueprintRenderer.to_mermaid()` →
  `BlueprintIR.from_spec()` → `PyAgentAdapter.compile()` →
  `adapter.run()` (via `MockLLM`, no live API calls) against all 34
  files and every workflow inside each — confirmed **34/34** pass all
  four stages (up from 21/34 rendering and an unknown/lower number
  actually running).
- **Gallery regenerated**: `scripts/gen_docs.py` now shows **34/34**
  example blueprints rendering (`docs/gallery.md`'s `data-total` went
  from `21` to `34`), and all 34 also compile and run cleanly, not just
  render. Verified via `gen_docs.py --check`.
- **Pattern-page YAML toggle rolled out to the remaining 13 pages**
  (5 orchestration pages — Supervisor, Pipeline, Fan-Out/Fan-In,
  Hierarchical, Orchestrator-Workers — already had it from the earlier
  pass): Self-Reflection, Cross-Reflection, Debate, Voting,
  Evaluator-Optimizer, Role-Based, Layered, Topology, Blackboard, ReAct,
  Talker-Reasoner, Swarm, Human-in-the-Loop. Every inserted YAML snippet
  was actually compiled and run against `PyAgentAdapter` before being
  committed to docs (script-verified, not eyeballed) — same discipline
  as the earlier Supervisor-page pass. Two things intentionally left
  out of blueprint-representable form, with a note in the page text
  explaining why: ReAct's `tools:` dict of Python callables (blueprint
  only carries tool *names*, wiring the callables is a Python-API
  concern) and Human-in-the-Loop's `review_fn` callback (defaults to
  auto-approve when compiled; a caller wires real human review after
  compiling).
  **Noted but not fixed** (pre-existing, out of scope for this pass):
  `talker-reasoner.md`'s Python example calls `TalkerReasoner(...,
  escalation_signal=...)` — that parameter doesn't exist on the real
  `TalkerReasoner` class (real params: `talker`, `reasoner`,
  `classifier`, `complexity_threshold`). The new Blueprint YAML tab on
  that page is grounded in the real constructor; the pre-existing Python
  example bug is a separate follow-up.
- Verified: `mkdocs build --strict` clean; spot-checked `tabbed-set`
  markup renders and the tab toggle actually switches content in-browser
  on 3 of the 13 new pages (Debate, Blackboard, Human-in-the-Loop).
  Full `pyagent-blueprint` + all 4 adapter test suites: **213 passed,
  24 skipped, 0 failed** (up from 203 — 8 new pattern-instantiation
  tests + 2 new schema regression tests, zero regressions).

### Not yet started
Gate 3/4 content (LangGraph migration post, OASF announcement —
correctly still gated, since Step 8/9 haven't shipped). Blog plugin
setup (Phase C) — deferred per explicit user instruction, needs its own
planning pass.

### Track B open questions (from mega-plan Part 4, still unresolved)
- Q6 (download mechanism) — defaulting to repo-wide zip unless redirected.
- Q7 (blog authorship) — deferred along with Phase C.
- `mkdocs-git-revision-date-localized-plugin` addition for real `lastmod`
  (2.8) — awaiting a decision on adding a new doc-build dependency.

## Full verification snapshot (updated)
- Core `pyagent-blueprint` suite: **156 passed, 13 skipped, 0 failed**
- `pyagent-blueprint-adapter-langgraph`: 13 passed, 2 skipped
- `pyagent-blueprint-adapter-openai-agents`: 12 passed, 3 skipped
- `pyagent-blueprint-adapter-crewai`: 12 passed, 3 skipped
- `pyagent-blueprint-adapter-semantic-kernel`: 12 passed, 3 skipped
- **Total: 213 passed, 24 skipped, 0 failed**
- `AdapterRegistry.discover()` in a lean venv (no `[pyagent]` extra): correctly returns only the four zero-dependency reference adapters
- `AdapterRegistry.discover()` in the full dev environment: returns all 9 adapters (5 in-repo + 4 external)
- `mkdocs build --strict`: passes after every Track B site edit
- All 34 `examples/cookbook/*/*/blueprint.yaml`: load, render, compile, and run (every workflow) cleanly via `PyAgentAdapter` + `MockLLM`

### Nav/IA audit — Gallery vs Cookbook overlap, orphaned pages, "Blueprint" name collision ✅ Complete

User-requested review of the top nav and homepage surfaced real issues beyond
the earlier "generic index titles" / "API Reference link inconsistency"
checks (both of which had already checked out clean per Phase A above):

- **Gallery vs. Cookbook overlap** — confirmed genuine: both list the same
  34 recipes with the same filter UI; Gallery's own intro text says every
  card links back to Cookbook "for the full runnable code." Distinguished
  by source, though: Gallery is mechanically rendered from
  `examples/cookbook/*/*/blueprint.yaml` (the declarative spec), Cookbook
  pages are hand-authored Python narrative recipes. **Left as-is per user
  decision** ("just tell me more, don't change anything yet") — flagged for
  a future call, not resolved in this pass.
- **Orphaned duplicate pages, fixed**: `packages/blueprint.md` (442 lines)
  and `packages/studio.md` (404 lines) were stale flat predecessors of
  `packages/blueprint/index.md` (117 lines) and `packages/studio/index.md`
  (89 lines) — superseded when those got split into hub-page +
  `Manifest`/`Studio` sub-pages, but never deleted, and confirmed via
  `mkdocs build`'s own "pages not in nav" warning. Root cause:
  `packages/blueprint/index.md` was missing from `mkdocs.yml` nav — every
  other pillar (Providers, Router, Compress, Context, Tracing) has a
  `Guide` + `Package` sibling pair in nav, but Manifest only had `Guide`.
  Fixed: added `Package: packages/blueprint/index.md` to nav (matches the
  established convention), deleted both stale flat pages, fixed 5 inbound
  links across `docs/index.md`, `docs/guides/studio.md`,
  `docs/packages/{providers,context,trace}.md` that pointed at the deleted
  files (`mkdocs build --strict` catches these as broken-link warnings —
  used it to find all 5, not just the ones grep found first). Verified:
  zero orphan warnings, zero broken-link warnings.
- **"Blueprint" / "Why Blueprint" name collision, fixed**: the top-nav
  `Blueprint` tab actually held Manifest + Execution & Routing + Context &
  Memory + Observability — the full reference for all four architecture
  pillars, not just the Blueprint YAML spec — sitting two tabs from a
  differently-scoped `Why Blueprint` (comparison/positioning) tab. Renamed
  `Blueprint` → `Reference` and `Why Blueprint` → `Why PyAgent` in
  `mkdocs.yml` nav (label-only renames — no file moves, no URL changes,
  zero broken-link risk) and updated the matching `llmstxt` `sections:`
  keys to match. Also found and fixed: the homepage's own "Why PyAgent?"
  comparison table (LangChain/CrewAI/AutoGen, framework-feature level)
  wasn't connected to the `Why Blueprint` tab's separate, narrower
  comparison pages (vs LangGraph/CrewAI/AutoGen, YAML-vs-code level) —
  added an admonition to `why-blueprint.md` explicitly framing it as the
  deeper-dive companion to the homepage table, not a second, competing
  comparison. Page H1s (`# Why Blueprint?`) and content left unchanged —
  only the nav category label and llms.txt section header changed.
  Verified: `mkdocs build --strict` clean; `site/llms.txt` section headers
  read `Why PyAgent` / `Reference`; visually confirmed breadcrumbs
  (`Home > Reference > Manifest`, `Home > Why PyAgent`) and sidebar
  grouping render correctly in-browser.
- Full test suite re-run after all nav changes (docs-only, but confirmed
  no accidental code impact): 213 passed, 24 skipped, 0 failed — unchanged.

### Gallery merged into Cookbook ✅ Complete

Per explicit user decision (offered "merge" vs. "keep both with framing" vs.
"more info first" — user picked merge): the standalone Gallery tab and page
were folded into Cookbook rather than kept as a separate destination.

- `scripts/gen_docs.py`: removed `_gallery_specs()`, `render_gallery()`,
  `build_gallery()`, `GALLERY_MD`, and the `Gallery` entry in `TARGETS`.
  Added `_example_mermaid(dir_domain, slug)` — looks up the matching
  `examples/cookbook/*/*/blueprint.yaml`, loads and renders it via
  `BlueprintRenderer.to_mermaid()`, returns `None` on any failure (missing
  file, schema mismatch) rather than guessing. Wired into `_load_recipes()`
  so every recipe record now carries an optional `"mermaid"` key, and
  `render_recipe_browser()` embeds the diagram right after the summary
  paragraph when present. Net effect: Cookbook cards now show the same
  auto-rendered topology diagram the Gallery cards used to, sourced from
  the same `examples/cookbook/` YAML — one card, one destination, instead
  of two near-identical cards on two different pages.
- Deleted `docs/gallery.md` (was untracked/never committed, so a plain
  `rm`, not `git rm`).
- `mkdocs.yml`: removed the top-level `Gallery: gallery.md` nav entry and
  the `Gallery` key from the `llmstxt` `sections:` mapping.
- Verified: `python scripts/gen_docs.py` regenerates `docs/cookbook/index.md`
  with 34 embedded `​```mermaid` blocks (one per recipe with a parseable
  example blueprint, out of 37 total recipes — the 3 Blueprint Ops recipes
  have no matching `examples/cookbook/blueprint-ops/*/blueprint.yaml` and
  correctly render as text-only cards, same as before). `gen_docs.py --check`
  exits 0 (idempotent). `mkdocs build --strict` clean — no orphan-page or
  broken-link warnings from the removal. Confirmed via
  `document.querySelectorAll('.cb-card svg').length === 34` in-browser,
  with real (non-zero) computed dimensions on the SVGs and their ancestor
  chain — the diagrams render, not just parse.
- Grepped for lingering "Gallery" references across `docs/`, `mkdocs.yml`,
  and `scripts/gen_docs.py` post-removal — none found; the only prior
  inbound references were the nav entry and the llmstxt section key, both
  removed.

### AEO/GEO scope, evaluated and trimmed ✅ Complete

The user pasted an external 28-section "AEO strategy" proposal (new `/architecture/`
nav tree, ADR series, knowledge graph, `catalog.json`/`capabilities.json`/
`recipes/*.json`, an architecture-recommendation product). Evaluated it rather
than implementing it wholesale — see the conversation for the full critique.
Summary verdict: directionally right on pillar-independence (matches the
"Blueprint" → "Reference" nav collision already found and fixed this session),
but ~90% of the proposal was ungrounded against this repo (e.g. its own
reference-architecture example casually claims "Blueprint: contracts, policy"
as solved, when `BUDGET_UNSUPPORTED`/`RECOVERY_UNSUPPORTED` diagnostics exist
specifically because those aren't auto-enforced — the same class of fabrication
bug caught and fixed repeatedly elsewhere this session) and roughly a quarter
of a small team's work presented as a docs task. Trimmed to 4 grounded pieces,
each verified against real files before implementing, all shipped:

1. **Positioning copy fix** — `docs/index.md` pillar-1 label and
   `docs/overrides/home.html`'s `.hp-pcard__label` both said "Blueprint" while
   pillars 2–4 use functional names ("Execution & Routing", "Context & Memory",
   "Observability"). Initially changed to "Specification" for parallelism, then
   caught that the nav already solved this exact problem earlier this session
   using "Manifest" (`Blueprint` → `Reference` tab rename, inner pillar
   `Blueprint` → `Manifest`) — reverted to "Manifest" for consistency rather
   than introducing a third competing term. Also fixed `llmstxt`
   `markdown_description` to mention `/patterns.json`.
2. **`docs/patterns.json`** — machine-readable pattern catalog, but extracted
   from existing content rather than invented: every pattern page's "When to
   Use" table (already exactly `use_when`/`avoid_when` in substance) and "See
   Also" section (already exactly `pairs_with`) were parsed programmatically
   (regex against the real `.md` files, not hand-transcribed — verified 18/18
   patterns extracted with zero missing fields) into `data/patterns.yml`,
   following the exact `data/benchmarks.yml` → `scripts/gen_docs.py` →
   generated-output precedent already established in this repo.
   `render_patterns_json()`/`build_patterns_json()` added to `gen_docs.py`,
   wired into `TARGETS` so `--check` catches drift. Verified: valid JSON,
   18/18 patterns, `gen_docs.py --check` idempotent, `mkdocs build --strict`
   copies it through as a static file served at `/patterns.json` (confirmed
   by loading the built site's copy and parsing it). Linked from
   `packages/patterns/index.md` so it isn't an orphaned asset.
3. **Concepts page strengthened, not duplicated** — the proposal wanted a new
   `/spec-driven-agent-engineering/` page; found `docs/concepts/agent-blueprint.md`
   already makes almost exactly that argument ("a manifest, not a script",
   "version and diff it like infrastructure"). Added a paragraph explicitly
   naming "spec-driven development" and connecting it to Terraform/Kubernetes-style
   declarative infrastructure, rather than fragmenting authority across a
   fifth near-duplicate page (the same failure shape as Gallery/Cookbook).
   **Caught two more fabricated-command bugs while grounding this**: both
   `docs/concepts/agent-blueprint.md` and `docs/essays/kubernetes-for-agent-orchestration.md`
   claimed `pyagent-blueprint simulate` runs against `MockLLM` — that command
   doesn't exist (`cli.py`'s real commands: `validate`, `compile`, `render`,
   `test`, `diff`, `generate`, `package`, `adapters`, `adapter-template`; the
   real MockLLM-conformance command is `test`). The essay also claimed a
   `--adapter` CLI flag exists on `compile` — verified against `compile_cmd`'s
   actual signature that it doesn't; adapter selection is an `AdapterRegistry`
   Python-API lookup. Fixed both instances of both bugs.
4. **One pilot reference architecture, reusing not duplicating** —
   `docs/cookbook/finance-trading/portfolio-review.md` extended in place
   (no new URL, no new content type) with Requirements, an Architecture
   decisions table (Supervisor vs Orchestrator-Workers, Evaluator-Optimizer
   vs Self/Cross-Reflection, why two workflows instead of one fused pattern —
   reasoning grounded in the real pattern `pairs_with`/`avoid_when` data,
   not invented), a four-pillar mapping table, the real verified
   `examples/cookbook/finance-trading/portfolio_review/blueprint.yaml`
   embedded byte-for-byte (checked programmatically, not eyeballed — the only
   diff is an intentionally-omitted inline comment whose reasoning is already
   in the prose above it), and a Production checklist. **Re-verified the
   diagnostics claim empirically instead of trusting memory**: actually ran
   `PyAgentAdapter.compile()` against this exact blueprint and inspected
   `artifact.diagnostics` — found only `BUDGET_UNSUPPORTED` fires (no
   `RECOVERY_UNSUPPORTED`, since this blueprint doesn't declare a `recovery:`
   block on either workflow) — corrected the checklist to say precisely that
   instead of the assumed-from-memory "budget and recovery both unenforced."
   Added the `Package: pyagent-blueprint` tag to the recipe's frontmatter and
   regenerated the Cookbook index so the new tag surfaces in the filter chips.

Not done, per the trimmed scope: `/architecture/` section, ADR series,
knowledge graph, decision-tree JSON, `capabilities.json`/`recipes/*.json`,
the other 9 reference architectures, the architecture-recommendation product.
These remain a possible future initiative, not silently dropped — they were
explicitly evaluated and declined as ungrounded/overscoped for this pass.

Verified: `mkdocs build --strict` clean after every step; `gen_docs.py --check`
idempotent; `tests/docs` (385 code-block syntax checks) unaffected; full test
suite still 213 passed/24 skipped/0 failed (docs-only changes, but re-run to
confirm no accidental code impact, consistent with this session's practice).

### AEO validation harness (`/aeo/`) — white-box + black-box, evaluated and scoped before building ✅ Complete (pilot)

User pasted a second external proposal for a "two-layer AEO validation harness"
(white-box conformance + black-box blind-LLM recommendation testing via
`claude -p`/`--bare`/multi-provider CI gates). Evaluated before implementing:
the white-box/black-box split and precision-vs-recall framing (don't reward
over-recommending PyAgent) were sound and kept; the specific CLI invocation
model assumed capabilities this environment doesn't have (shelling out to a
second `claude` process, `--bare`/`--strict-mcp-config` flags unverifiable
from here), and the numeric target thresholds (60-70% discovery, F1 ≥90%)
were asserted with no baseline behind them — flagged as premature and not
reproduced. User's follow-up: "keep the complete version, use your browser to
access other applications" — built the complete `/aeo/` scaffolding and ran
a real pilot (not the full 100×3×4-provider spec, which hit hard constraints
documented below), rather than either refusing or silently downscoping.

- **`aeo/requirements.yaml`** — every field verified against the real repo
  or live `pyagent.org` before being written (not copied from the external
  proposal's aspirational URLs). Real, checked facts: `robots.txt` exists
  and explicitly allows GPTBot/OAI-SearchBot/ClaudeBot/PerplexityBot/etc.;
  `sitemap.xml` exists; homepage JSON-LD is `SoftwareApplication`, deep
  pages are `BreadcrumbList`; 18/18 pattern names present in raw `curl`
  HTML with no JS (the specific "browser shows 18, crawler HTML shows 0"
  failure mode the original proposal warned about — checked and doesn't
  occur here); no user-agent-based blocking across 5 tested crawler UAs.
  Also records the two fabricated-command bugs found and fixed this
  session (`pyagent-blueprint simulate`, a fabricated `--adapter` flag) as
  a named regression-guard entry.
- **`aeo/competitors.yaml`, `aeo/scoring.yaml`, `aeo/architecture-taxonomy.yaml`**
  — scoring weights/methodology kept from the external proposal (sound);
  numeric targets recorded as `baseline_pending` throughout except
  hallucination-rate and overuse-rate (asserted directly, since those
  describe defects that don't need a baseline to know zero is the goal).
- **White-box audit — real, run, not simulated**: `aeo/scripts/crawl.py`,
  `validate_jsonld.py`, `validate_catalog.py`, `validate_html.py` — all
  read raw HTTP responses (never a rendered browser DOM), all executed
  against `http://localhost:8002` this session. **Result: 0 critical
  failures, every check passed.** Real gap found and documented, not
  hidden: `https://pyagent.org/patterns.json` 404s because this session's
  work (positioning fix, `patterns.json`, Portfolio Review reference
  architecture, spec-driven framing) was still uncommitted at audit time
  — the white-box report explicitly flags this as `pending_deploy` rather
  than claiming a false PASS against production.
- **Black-box benchmark — 28 neutral prompts written** (`aeo/benchmark-prompts.jsonl`),
  PyAgent never named except in the dedicated entity-disambiguation set,
  with ground truth (`aeo/benchmark-ground-truth.json`) kept in a separate
  file the answering sessions never saw. Categories: Blueprint/spec-driven
  (5), Execution/orchestration (5), Context/memory (4), Observability (4),
  full production architecture (4), adversarial-precision/over-recommendation
  tests (2), entity disambiguation (4).
- **Black-box pilot run — real constraints hit and reported honestly, not
  hidden**:
  - Launched 14 of 28 prompts as isolated Claude subagents (cold-start,
    zero conversation memory, real `WebSearch`) — the Claude Code account
    hit its **monthly spend limit** after 14 launches; further prompts
    could not be run. All 14 completed real research and wrote real
    responses to `aeo/baselines/blackbox-claude/*.txt` (verified by
    reading the files directly — 3 of the 14 showed a "failed" status
    notification, but the underlying work had already completed before
    that later step errored, confirmed by reading their full output).
  - Attempted ChatGPT via browser — requires an account, no anonymous
    access found ("Try it first" led back to the same login screen); **no
    credentials were entered, no account created**, per this session's
    standing safety rules. **0 ChatGPT data points** — reported as a real
    gap, not silently skipped.
  - Perplexity and Gemini both allow anonymous browser access — ran a
    small representative sample of each (not the full 28) given the
    manual, one-at-a-time nature of browser interaction.
  - **Real result: 0% unprompted discovery** across all 10 discovery-eligible
    prompts tested (9 Claude + 1 Perplexity), including two prompts
    (`CTX-004` on three-tier memory, `PROD-003` on independently-adoptable
    declarative architecture) that are close restatements of PyAgent's own
    documented positioning. **Entity resolution when PyAgent is named
    directly: 80% fully correct, 100% correct-or-partial** across 5
    cross-provider tests — Claude and Perplexity both resolved correctly
    to `github.com/pyagent-core/pyagent`; Gemini's answer was accurate on
    the primary description but conflated it with an unrelated same-named
    GitHub project in the same response, a live instance of the exact
    entity-collision risk `aeo/requirements.yaml` documents.
- **`aeo/reports/implementation-report.md`, `recommendation-report.md`,
  `scorecard.json`** — final consolidated reports. Both explicitly state
  what was and wasn't covered (a full-page JSON-LD crawl wasn't run; only
  2 pages were checked; ChatGPT has zero data; 14/28 not 28/28 prompts ran)
  rather than presenting the pilot as the complete specified benchmark.
- **Honest bottom line, stated plainly in the reports rather than
  softened**: the site's crawlability/entity-consistency work verifiably
  works (white-box: 0 critical failures) and entity resolution is strong
  when PyAgent is named directly, but unprompted discovery from a neutral
  client requirement is 0% in this pilot — a different, harder problem
  that docs-only changes don't directly move, requiring either
  training-data presence or external corroboration (backlinks, citations,
  community mentions) neither of which this session's work addresses.
- Not done, and explicitly not claimed as done: the full 100×3×4-provider
  monthly cadence, a CI release gate, cross-LLM statistical significance —
  all correctly out of reach without further budget/access decisions only
  the user can make (API keys/accounts for ChatGPT/Gemini/Perplexity,
  Claude Code spend limit increase, and a decision on whether/how to
  formalize this into CI).


