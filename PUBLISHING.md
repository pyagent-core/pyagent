# Publishing Guide

Step-by-step instructions for publishing PyAgent packages to PyPI from the
`pyagent-core/pyagent` GitHub repository.

---

## Prerequisites

- GitHub organisation **`pyagent-core`** exists and you have admin access
- PyPI account (https://pypi.org) — create a separate account per package project
  or use one account for all; Trusted Publishers work either way
- `uv` installed locally (`pip install uv` or via the official installer)

---

## 1 — Push to GitHub

```bash
cd /path/to/pyagent

git init
git add .
git commit -m "chore: initial release v0.1.0"

# Create the repo on GitHub first:  https://github.com/new
# Organisation: pyagent-core   Repository name: pyagent

git remote add origin https://github.com/pyagent-core/pyagent.git
git branch -M main
git push -u origin main
```

---

## 2 — Set up PyPI Trusted Publishers (OIDC — no API key needed)

Do this **once per package** before the first publish.

For each of the 5 packages, go to:
```
https://pypi.org/manage/account/publishing/
```
(or navigate: PyPI → your account → Publishing → Add a new pending publisher)

Fill in:
| Field | Value |
|---|---|
| PyPI Project Name | `pyagent-patterns` (repeat for each package) |
| Owner | `pyagent-core` |
| Repository name | `pyagent` |
| Workflow filename | `publish.yml` |
| Environment name | `pypi` |

Repeat for: `pyagent-compress`, `pyagent-router`, `pyagent-trace`, `pyagent-all`

---

## 3 — Create the `pypi` environment in GitHub

1. Go to `https://github.com/pyagent-core/pyagent/settings/environments`
2. Click **New environment** → name it `pypi`
3. (Optional) Add a protection rule: require a reviewer before publishing

---

## 4 — Release a new version

### a) Bump versions
Update `version = "..."` in all 5 `packages/*/pyproject.toml` files (and the
inter-package dependency pins if you're bumping a major version).

### b) Update CHANGELOG.md
Move items from `[Unreleased]` to a new `[x.y.z]` section.

### c) Commit and tag
```bash
git add .
git commit -m "chore: release v0.2.0"
git tag v0.2.0
git push origin main --tags
```

Pushing the tag triggers `.github/workflows/publish.yml` automatically.

### d) Watch CI
Check `https://github.com/pyagent-core/pyagent/actions` — the **Publish to PyPI**
workflow will:
1. Build all 5 packages (`uv build --package ...`)
2. Publish them to PyPI in dependency order (patterns → compress/router/trace → all)

---

## 5 — Verify on PyPI

After the workflow succeeds:
```
https://pypi.org/project/pyagent-patterns/
https://pypi.org/project/pyagent-compress/
https://pypi.org/project/pyagent-router/
https://pypi.org/project/pyagent-trace/
https://pypi.org/project/pyagent-all/
```

Test the install locally:
```bash
pip install pyagent-patterns==0.1.0
pip install pyagent-all==0.1.0
```

---

## Local test-build (before releasing)

```bash
# Build a single package
uv build --package pyagent-patterns --out-dir /tmp/dist/pyagent-patterns

# Inspect the wheel
unzip -l /tmp/dist/pyagent-patterns/*.whl

# Test install from local wheel
pip install /tmp/dist/pyagent-patterns/*.whl
```
