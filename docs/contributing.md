---
description: "How to contribute to PyAgent — development setup, running tests, code style, and adding new patterns or cookbook examples."
---

# Contributing

## Development Setup

```bash
git clone https://github.com/pyagent/pyagent.git
cd pyagent

# Install all packages in development mode
pip install -e packages/pyagent-patterns[dev]
pip install -e packages/pyagent-router[dev]
pip install -e packages/pyagent-compress[dev]
pip install -e packages/pyagent-trace[dev]
```

## Running Tests

```bash
# All tests
PYTHONPATH=packages/pyagent-patterns/src:packages/pyagent-router/src:packages/pyagent-compress/src:packages/pyagent-trace/src \
  python -m pytest packages/ -v

# Specific package
python -m pytest packages/pyagent-patterns/tests/ -v
```

## Code Style

- **Ruff** for linting and formatting (configured in root `pyproject.toml`)
- **mypy** for type checking (strict mode)
- **async-first** — all pattern `_execute` methods are async
- Docstrings follow Google style

```bash
ruff check packages/
ruff format packages/
mypy packages/pyagent-patterns/src/
```

## Adding a New Pattern

1. Create `packages/pyagent-patterns/src/pyagent_patterns/<tier>/<pattern_name>.py`
2. Subclass `Pattern` and implement `pattern_type` property and `_execute()` method
3. Export from `<tier>/__init__.py`
4. Register in `registry.py`
5. Add tests in `packages/pyagent-patterns/tests/test_<tier>.py`
6. Add docs page in `docs/packages/patterns/<tier>/<pattern-name>.md` with:
    - Mermaid sequence diagram
    - Code example
    - When to Use / Avoid table
    - Cost-effectiveness table

## Adding a Cookbook Example

The [Cookbook](cookbook/index.md) is a growing library of complete, runnable multi-agent recipes
organized by domain. To add one:

1. Create `docs/cookbook/<domain>/<example-slug>.md` (e.g. `docs/cookbook/finance-trading/portfolio-review.md`).
2. Give it a **prompt-shaped title** — phrase the `# H1` and the frontmatter `description` the way a
   developer would search or prompt for it (e.g. *"How to build a multi-agent portfolio review workflow in Python"*).
3. Add `summary`, `complexity`, and prefixed `tags:` on **three axes** (Domain / Pattern / Package)
   so the recipe appears in the [filterable Cookbook browser](cookbook/index.md) and on the
   matching pattern pages:

    ```yaml
    ---
    description: "How to build a multi-agent portfolio review workflow in Python with PyAgent."
    summary: "Analyst panel with an evaluator-optimizer quality gate"
    complexity: Intermediate     # Beginner | Intermediate | Advanced
    tags:
      - "Domain: Finance & Trading"
      - "Pattern: Supervisor"
      - "Pattern: Evaluator-Optimizer"
      - "Package: pyagent-patterns"
    ---
    ```

4. Follow the example template: **problem statement → pattern(s) used → full runnable code
   (open with the exact `pip install` and `import` lines) → expected output / OTel trace →
   Related examples / Patterns used cross-links.**
5. Run `python scripts/gen_docs.py` so the recipe is added to the Cookbook browser and the
   "Cookbook recipes" section of every pattern it uses.
6. Run `DISABLE_MKDOCS_2_WARNING=true mkdocs build --strict` — it must pass (catches broken links).

Use real package names only (`pyagent-patterns`, `pyagent-all`, …) so the examples stay copy-paste-runnable.

## Documentation

```bash
pip install mkdocs-material mkdocstrings[python] mkdocs-redirects mkdocs-llmstxt
mkdocs serve  # Preview at http://localhost:8000
```

### Generated pages

The benchmark tables on `docs/benchmarks.md`, the filterable recipe browser on
`docs/cookbook/index.md`, and the "Cookbook recipes" sections on each pattern page
are **generated** — the regions between `<!-- gen:NAME:start -->` /
`<!-- gen:NAME:end -->` markers are computed from `data/benchmarks.yml` and each
recipe's frontmatter, so tables, cards, and cross-references can't drift. Edit the
data source (or the recipe), not the generated region, then regenerate:

```bash
python scripts/gen_docs.py          # rewrite generated regions
python scripts/gen_docs.py --check  # CI uses this; fails if out of sync
```

## Package Structure

```
pyagent/
├── packages/
│   ├── pyagent-patterns/     # Core: 18 patterns + composites + guardrails + recovery
│   ├── pyagent-router/       # Difficulty scoring + model selection
│   ├── pyagent-compress/     # Message compression + token budgets
│   └── pyagent-trace/        # OTel spans + cost tracking + replay
├── docs/                     # MkDocs Material site
├── mkdocs.yml
└── pyproject.toml            # Workspace root
```
