#!/usr/bin/env python3
"""Regenerate computed sections of the docs from structured sources.

Two generated areas, each delimited by ``<!-- gen:NAME:start ... -->`` /
``<!-- gen:NAME:end -->`` markers in the target Markdown:

* **docs/benchmarks.md** — the Cost-Effectiveness, Quality, and Router Savings
  tables are computed from ``data/benchmarks.yml``. Ratios, per-tier savings,
  and the weighted "Mixed" router figure are derived here, never hand-typed,
  which is what prevents the inconsistent-number class of bug.
* **docs/cookbook/index.md** — the coverage sentence ("N of M domains…") and
  the domain list (with _coming soon_ markers) are computed from the actual
  directory layout under ``docs/cookbook/``, so the page can never claim more
  coverage than exists.

Usage::

    python scripts/gen_docs.py            # rewrite the generated regions
    python scripts/gen_docs.py --check    # exit 1 if regions are out of sync

CI runs ``--check`` so a stale commit fails the build.
"""

from __future__ import annotations

import argparse
import html
import re
import sys
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "benchmarks.yml"
BENCHMARKS_MD = ROOT / "docs" / "benchmarks.md"
COOKBOOK_INDEX = ROOT / "docs" / "cookbook" / "index.md"
COOKBOOK_DIR = ROOT / "docs" / "cookbook"


def _round2(value: float) -> Decimal:
    """Round half-up to 2 decimals (so 0.225 -> 0.23, matching the published tables)."""
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _round_pct(value: float) -> int:
    """Round a 0-1 fraction to a whole percent, half-up."""
    return int((Decimal(str(value)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


# ── Block replacement ────────────────────────────────────────────────────────


def replace_region(text: str, name: str, new_body: str) -> str:
    """Replace the content between the start/end markers for ``name``."""
    pattern = re.compile(
        rf"(<!-- gen:{re.escape(name)}:start[^\n]*-->)(.*?)(<!-- gen:{re.escape(name)}:end -->)",
        re.DOTALL,
    )
    if not pattern.search(text):
        raise SystemExit(f"marker pair for '{name}' not found in target file")
    return pattern.sub(lambda m: f"{m.group(1)}\n{new_body}\n{m.group(3)}", text)


# ── Benchmarks tables ────────────────────────────────────────────────────────


def render_cost_effectiveness(data: dict) -> str:
    rate = data["cost_per_token_usd"]
    lines = [
        "| Pattern | Avg Tokens/Task | Avg Cost/Task | Notes |",
        "|---------|----------------|---------------|-------|",
    ]
    for row in data["cost_effectiveness"]:
        cost = row["avg_tokens"] * rate
        lines.append(f"| {row['pattern']} | {row['avg_tokens']} | ${cost:.6f} | {row['note']} |")
    return "\n".join(lines)


def render_quality(data: dict) -> str:
    q = data["quality"]
    baseline = q["baseline_pattern"]
    lines = [
        "| Pattern | Avg Quality Score | Cost Multiplier | Quality/Cost Ratio |",
        "|---------|------------------|----------------|--------------------|",
    ]
    for row in q["rows"]:
        mult = row["cost_multiplier"]
        if row["pattern"] == baseline:
            ratio_cell = "Baseline"
        else:
            ratio = (row["quality_pct"] / 100) / mult
            ratio_cell = f"{_round2(ratio)}×"  # noqa: RUF001 (multiplication sign is intended)
        lines.append(
            f"| {row['pattern']} | {row['quality_pct']}% | {mult:.1f}× | {ratio_cell} |"  # noqa: RUF001
        )
    return "\n".join(lines)


def render_router(data: dict) -> str:
    r = data["router"]
    base_model = r["baseline_model"]
    base_cost = r["baseline_cost_usd"]
    tiers = {t["difficulty"]: t for t in r["tiers"]}
    lines = [
        "| Task Difficulty | Without Router | With Router | Savings |",
        "|----------------|---------------|-------------|---------|",
    ]
    for t in r["tiers"]:
        savings = _round_pct((base_cost - t["cost_usd"]) / base_cost)
        lines.append(
            f"| {t['difficulty']} | {base_model} (${base_cost}) | "
            f"{t['model']} (${t['cost_usd']}) | {savings}% |"
        )
    mixed = r["mixed"]
    weighted = sum(
        weight * tiers[name]["cost_usd"] for name, weight in mixed["distribution"].items()
    )
    mixed_savings = _round_pct((base_cost - weighted) / base_cost)
    # Trim trailing zeros from the weighted cost for a tidy display ($0.00023).
    weighted_str = format(weighted, ".5f").rstrip("0").rstrip(".")
    lines.append(
        f"| **{mixed['label']}** | **${base_cost}** | **${weighted_str}** | **{mixed_savings}%** |"
    )
    return "\n".join(lines)


def build_benchmarks(text: str) -> str:
    data = yaml.safe_load(DATA.read_text(encoding="utf-8"))
    text = replace_region(text, "cost_effectiveness", render_cost_effectiveness(data))
    text = replace_region(text, "quality", render_quality(data))
    text = replace_region(text, "router", render_router(data))
    return text


# ── Cookbook recipe browser (landing page) ───────────────────────────────────


def _esc(s: str) -> str:
    return html.escape(str(s), quote=True)


def render_recipe_browser() -> str:
    """Filterable recipe cards for the Cookbook landing page.

    Each card also embeds a live Mermaid topology diagram rendered straight
    from the recipe's example ``blueprint.yaml`` via ``BlueprintRenderer``
    (never hand-drawn), when a parseable example exists for it — folded in
    from the former standalone Gallery page, which was near-duplicate
    content (same 34 recipes, same filter UI) with no framing explaining
    why it was a separate destination.

    Pure HTML (no inner markdown) so md_in_html passes it through verbatim;
    `recipe-filter.js` builds the facet bar from the cards' ``data-*`` and the
    hrefs are directory URLs (validated by linkchecker, not by mkdocs --strict).
    """
    recipes = _load_recipes()
    recipes.sort(key=lambda r: (r["domain"], r["title"]))

    out = [
        '<div id="recipe-filter-bar"></div>',
        "",
        f'<div id="recipe-browser" data-total="{len(recipes)}">',
    ]
    for r in recipes:
        chips = [
            f'<button class="cb-chip cb-chip--domain" data-axis="Domain" '
            f'data-value="{_esc(r["domain"])}">{_esc(r["domain"])}</button>'
        ]
        chips += [
            f'<button class="cb-chip cb-chip--pattern" data-axis="Pattern" '
            f'data-value="{_esc(p)}">{_esc(p)}</button>'
            for p in r["patterns"]
        ]
        chips += [
            f'<button class="cb-chip cb-chip--package" data-axis="Package" '
            f'data-value="{_esc(p)}">{_esc(p)}</button>'
            for p in r["packages"]
        ]
        cx = r["complexity"]
        out += [
            f'<article class="cb-card" data-domain="{_esc(r["domain"])}" '
            f'data-pattern="{_esc("|".join(r["patterns"]))}" '
            f'data-package="{_esc("|".join(r["packages"]))}">',
            f'<h3 class="cb-card__title"><a href="{r["rel"]}/">{_esc(r["title"])}</a>'
            f' <span class="cb-cx cb-cx--{cx.lower()}">{_esc(cx)}</span></h3>',
            f'<p class="cb-summary">{_esc(r["summary"])}</p>',
        ]
        if r.get("mermaid"):
            out += ["```mermaid", r["mermaid"], "```"]
        out += [
            '<p class="cb-chips">' + "".join(chips) + "</p>",
            "</article>",
        ]
    out.append("</div>")
    return "\n".join(out)


def build_cookbook(text: str) -> str:
    return replace_region(text, "recipe_browser", render_recipe_browser())


# ── Pattern → Cookbook cross-references ──────────────────────────────────────

PATTERNS_DIR = ROOT / "docs" / "packages" / "patterns"

# Pattern page slug → the canonical display name used in recipe `Pattern:` tags.
# Hardcoded because two pages (layered, role-based) have "… Cooperation" H1s, so
# parsing the heading is unreliable.
_PATTERN_SLUG_TO_NAME = {
    "supervisor": "Supervisor",
    "pipeline": "Pipeline",
    "fan-out-fan-in": "Fan-Out / Fan-In",
    "hierarchical": "Hierarchical",
    "orchestrator-workers": "Orchestrator-Workers",
    "self-reflection": "Self-Reflection",
    "cross-reflection": "Cross-Reflection",
    "debate": "Debate",
    "voting": "Voting",
    "evaluator-optimizer": "Evaluator-Optimizer",
    "role-based": "Role-Based",
    "layered": "Layered",
    "topology": "Topology",
    "blackboard": "Blackboard",
    "react": "ReAct",
    "talker-reasoner": "Talker-Reasoner",
    "swarm": "Swarm",
    "human-in-the-loop": "Human-in-the-Loop",
}

# Recipe slug → short display title (matches the Cookbook nav labels; handles
# initialisms the slug can't, e.g. SQL, CV, and the renamed "Alert Triage").
_RECIPE_SLUG_TO_TITLE = {
    "support-router": "Support Router",
    "sql-analyst": "SQL Analyst",
    "incident-triage": "Incident Triage",
    "portfolio-review": "Portfolio Review",
    "clinical-summary": "Clinical Summary",
    "cv-screener": "CV Screener",
    "contract-review": "Contract Review",
    "campaign-planner": "Campaign Planner",
    "research-assistant": "Research Assistant",
    "lead-qualifier": "Lead Qualifier",
    "log-triage": "Alert Triage",
    "code-review": "Code Review",
    # Wave A — fill every empty domain + pattern
    "product-launch-planner": "Product Launch Planner",
    "essay-grader": "Essay Grading by Consensus",
    "npc-world": "Emergent NPC World",
    "policy-briefing": "Policy Briefing Pipeline",
    "writers-room": "Writers' Room",
    "property-valuation": "Property Valuation Stack",
    "peer-review": "Peer-Review Mesh",
    "trip-planner": "Trip-Planning Swarm",
    # Wave B — competitor-signature examples
    "startup-simulation": "Software Startup Simulation",
    "onboarding": "Customer Onboarding Workflow",
    "loan-underwriting": "Loan Underwriting Committee",
    "loan-origination": "Loan Origination Workflow",
    "compliance-checker": "Regulatory Compliance Checker",
    "fraud-investigation": "Fraud Investigation Assistant",
    "literature-review": "Literature Review Team",
    "analytics-decomposer": "Analytics Task Decomposer",
    # Finance & Trading deep-dive recipes
    "wealth-rebalancing": "Wealth Rebalancing Crew",
    "esg-analyzer": "ESG Report Analyzer",
    "aml-monitoring": "AML Transaction Monitoring",
    "trading-signals": "Trading Signal Desk",
    "earnings-call": "Earnings Call Analyzer",
    "robo-advisor": "Robo-Advisor Onboarding",
}

_COMPLEXITY_ORDER = {"Beginner": 0, "Intermediate": 1, "Advanced": 2}


def _recipe_frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    return yaml.safe_load(text[3:end]) or {}


EXAMPLES_DIR = ROOT / "examples" / "cookbook"


def _example_mermaid(dir_domain: str, slug: str) -> str | None:
    """Best-effort: render the Mermaid diagram from this recipe's example
    ``blueprint.yaml``, if one exists and still parses against the current
    schema. Returns None otherwise (the recipe card just omits the diagram
    rather than guessing at one) — some example files predate the current
    schema and fail validation; see IMPLEMENTATION-STATUS.md.
    """
    path = EXAMPLES_DIR / dir_domain / slug.replace("-", "_") / "blueprint.yaml"
    if not path.exists():
        return None
    try:
        from pyagent_blueprint.loader import load_blueprint
        from pyagent_blueprint.renderer import BlueprintRenderer

        spec = load_blueprint(str(path.relative_to(ROOT)))
        return BlueprintRenderer().to_mermaid(spec)
    except Exception:
        return None


def _load_recipes() -> list[dict]:
    """Parse each cookbook recipe's tags/summary/complexity into a flat record."""
    recipes: list[dict] = []
    for md in sorted((ROOT / "docs" / "cookbook").glob("*/*.md")):
        if md.name == "index.md":
            continue
        fm = _recipe_frontmatter(md)
        tags = fm.get("tags", []) or []
        patterns = [t.split(":", 1)[1].strip() for t in tags if t.startswith("Pattern:")]
        if not patterns:
            continue
        domain = next(
            (t.split(":", 1)[1].strip() for t in tags if t.startswith("Domain:")),
            md.parent.name,
        )
        packages = [t.split(":", 1)[1].strip() for t in tags if t.startswith("Package:")]
        slug = md.stem
        recipes.append(
            {
                "patterns": patterns,
                "packages": packages,
                "domain": domain,
                "title": _RECIPE_SLUG_TO_TITLE.get(slug, slug.replace("-", " ").title()),
                "summary": fm.get("summary", ""),
                "complexity": fm.get("complexity", "Intermediate"),
                "rel": f"{md.parent.name}/{slug}",  # relative path under docs/cookbook/
                "mermaid": _example_mermaid(md.parent.name, slug),
            }
        )
    return recipes


def render_pattern_cookbooks(pattern_name: str, recipes: list[dict]) -> str:
    """Render the 'Cookbook recipes' section body for one pattern page."""
    matching = [r for r in recipes if pattern_name in r["patterns"]]
    matching.sort(key=lambda r: (_COMPLEXITY_ORDER.get(r["complexity"], 1), r["title"]))

    lines = ["## Cookbook recipes", ""]
    if not matching:
        lines.append(
            "_No cookbook recipes use this pattern yet — browse the "
            "[Cookbook](../../../cookbook/index.md) or "
            "[contribute one](../../../contributing.md)._"
        )
        return "\n".join(lines)

    lines += [
        f"Complete, runnable examples that use the **{pattern_name}** pattern:",
        "",
        "| Recipe | Domain | What it does | Complexity |",
        "|--------|--------|--------------|------------|",
    ]
    for r in matching:
        link = f"[{r['title']}](../../../cookbook/{r['rel']}.md)"
        lines.append(f"| {link} | {r['domain']} | {r['summary']} | {r['complexity']} |")
    return "\n".join(lines)


def make_pattern_builder(pattern_name: str):
    """Return a builder(text) that fills the `cookbooks` region for one pattern."""

    def build(text: str) -> str:
        return replace_region(
            text, "cookbooks", render_pattern_cookbooks(pattern_name, _load_recipes())
        )

    return build


# ── Driver ───────────────────────────────────────────────────────────────────

TARGETS = [
    (BENCHMARKS_MD, build_benchmarks),
    (COOKBOOK_INDEX, build_cookbook),
]

# One target per pattern page (path → its display name via the slug map).
for _page in sorted(PATTERNS_DIR.glob("*/*.md")):
    _name = _PATTERN_SLUG_TO_NAME.get(_page.stem)
    if _name:
        TARGETS.append((_page, make_pattern_builder(_name)))


def main() -> int:
    parser = argparse.ArgumentParser(description="Regenerate computed docs sections")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Do not write; exit 1 if any target is out of sync.",
    )
    args = parser.parse_args()

    stale: list[str] = []
    for path, builder in TARGETS:
        current = path.read_text(encoding="utf-8")
        updated = builder(current)
        if current != updated:
            if args.check:
                stale.append(str(path.relative_to(ROOT)))
            else:
                path.write_text(updated, encoding="utf-8")
                print(f"regenerated {path.relative_to(ROOT)}")

    if args.check and stale:
        print("Out of sync with their data sources (run `python scripts/gen_docs.py`):")
        for s in stale:
            print(f"  - {s}")
        return 1
    if not args.check:
        print("done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
