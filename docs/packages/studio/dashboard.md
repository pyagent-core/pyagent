---
description: "The PyAgent Studio dashboard — overview KPIs, traces, costs, governance, and provider health in one web UI."
---

# Studio — Web Dashboard

```bash
pyagent dashboard
# Web UI available at http://localhost:8000
```

The web dashboard exposes every Studio capability through a browser — designed for team members who don't live in a terminal, and for visual inspection of complex multi-agent systems.

---

## /overview

Blueprint summary and quick-action panel.

```
Blueprint: customer-support-system v1.2.0
Owner: platform-team  |  Tags: support, production

Resources
  Agents:     5   Workflows:  1
  Providers:  3   Contracts:  2

Compliance Score: 83%  (5/6 checks passed)

[Validate]  [Simulate]  [View Traces]  [View Diff]
```

The compliance score comes from `GovernanceService` — see [Services](services.md#governanceservice). Click **Validate** to rerun checks live. Click **Simulate** to jump to `/simulate` with the current blueprint pre-loaded.

---

## /agents

Agent roster with full prompt viewer.

```
Agents (5)

classifier          fast / claude-haiku-3-5-20241022
  Route to billing, technical, returns, or general

  System prompt:
    Classify the customer message into exactly one of:
    billing, technical, returns, general.
    Respond with ONLY the category name.

billing_agent       expert / claude-sonnet-4-20250514
  Handle billing disputes and subscription issues

  System prompt:
    You are a billing specialist. Handle disputes, refunds,
    and subscription questions. Always acknowledge frustration first.
    ...

  Tools: lookup_invoice, issue_refund
```

Each agent card shows:
- Name, description, provider, model
- Full system prompt (expandable)
- Tools and guardrails attached

---

## /workflows

Pattern diagrams with interactive agent inspection.

```
Workflows (1)

main  [supervisor]  ── [Run Simulation]

    flowchart TD
        IN[Input] --> classifier
        classifier -->|billing| billing_agent
        classifier -->|technical| technical_agent
        ...
        formatter --> OUT[Output]
```

- Rendered Mermaid diagram for each workflow
- Click any agent node to see its prompt and provider inline
- Pattern type badge: `supervisor`, `pipeline`, `fan_out_fan_in`, etc.
- **Run Simulation** button launches `/simulate` with this workflow pre-selected

---

## /simulate {#simulate}

Interactive workflow runner.

```
Workflow: [main ▼]
Mode:     [◉ Mock (free)]  [○ Live (real API)]

Task:     [I was charged twice this month          ]   [Run]

─────────────────────────────────────────────────────
Step 1  classifier        0.012s  MockLLM
  Output: billing

Step 2  billing_agent     0.024s  MockLLM
  Output: "I understand your frustration. Let me look into the
          double charge on your account..."

Step 3  formatter         0.008s  MockLLM
  Output: "Thank you for reaching out. I understand your frustration
          regarding the duplicate charge..."
─────────────────────────────────────────────────────
Final:    "Thank you for reaching out. I understand..."
Duration: 0.044s  |  Cost: $0.00 (mock)  |  Route: billing
```

Switch between Mock and Live mode. Live mode uses real providers and shows actual latency and cost.

---

## /traces

Trace explorer for recorded `.jsonl` files.

See the dedicated [Traces page](traces.md) for full detail.

```
Loaded: traces/production_runs.jsonl
1,240 spans  |  180 runs  |  last run: 2025-06-09T14:32

Run #174   supervisor   3 steps   3.4s   $0.0092
├── classifier     0.3s  claude-haiku   12→1 tok    $0.00001
├── billing_agent  2.4s  claude-sonnet  180→140 tok $0.00840
└── formatter      0.7s  claude-haiku   145→80 tok  $0.00051

Cost by model (last 7 days):
  claude-sonnet-4-20250514 ████████████████  $24.80 (72%)
  gpt-4o-mini              ████              $6.20  (18%)
  claude-haiku-3-5-20241022 ██               $3.40  (10%)
```

---

## /governance

Compliance scores and diff view.

```
Blueprint: customer-support-system v1.2.0
Compliance Score: 83%  (5/6 checks passed)

✓ Agent refs       All workflow agent references resolve
✓ Provider refs    All agent provider references resolve
✓ Pattern names    All patterns are registered
✓ Contract refs    All contract references resolve
✗ SLA values       timeout_seconds: 30s may be too low for expert provider
                   (claude-sonnet p99 observed at 2.4s)
✓ Security         No hardcoded API keys detected

Diff vs previous version:
  ~ agents.billing_agent.provider: expert → premium  (+$0.008/call)
  - agents.legacy_agent  (removed)
```

---

## /providers {#providers}

Real-time provider health and budget dashboard.

```
Provider Health

anthropic / claude-haiku-3-5-20241022
  Status: ✓ HEALTHY   Avg latency: 340ms   p99: 820ms
  Errors (1h): 0   Budget used: $1.24 / $50.00  ██░░░░░░░░  2.5%

anthropic / claude-sonnet-4-20250514
  Status: ✓ HEALTHY   Avg latency: 1,100ms   p99: 2,400ms
  Errors (1h): 2 (rate limit)   Budget used: $18.60 / $50.00  ██████░░░  37%

openai / gpt-4o-mini
  Status: ✓ HEALTHY   Avg latency: 480ms   p99: 1,100ms
  Errors (1h): 0   Budget used: $4.30 / $50.00  █░░░░░░░░░  9%
```

Budget data comes from the `cost_budget.daily_usd` field in the blueprint's `observability:` block.

---

## /diff

Visual semantic diff between two blueprint versions.

Upload two YAML files or paste YAML directly into the editor panels. Changes are categorized:

- **BREAKING** — pattern changed, required field removed
- **WARNING** — prompt changed, provider swapped
- **INFO** — metadata, descriptions, tags

---

## /docs

Auto-generated documentation for the loaded blueprint — produced by `BlueprintRenderer.to_markdown()`. Exportable as a Markdown file.

---

## Launching with a Blueprint Pre-Loaded

```bash
# Load blueprint and traces on startup
pyagent dashboard \
  --blueprint customer-support.yaml \
  --trace traces/production_runs.jsonl \
  --port 8000
```

---

## See Also

- [CLI](cli.md) — terminal-first access to the same operations
- [Services](services.md) — the Python layer powering the dashboard
- [Traces](traces.md) — trace file format and exploration
