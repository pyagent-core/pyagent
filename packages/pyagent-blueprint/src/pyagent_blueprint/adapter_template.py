"""Adapter template scaffold generation (Step 7).

Generates a minimal, ready-to-publish starter package for a third-party
`RuntimeAdapter` implementation: a `pyproject.toml` with the entry point
pre-wired, a stub adapter module, and a test file that already imports
and runs the shared `AdapterConformanceSuite` — the acceptance bar any
new adapter (LangGraph, AutoGen, CrewAI, Semantic Kernel, OpenAI Agents
SDK, or an in-house runtime) must pass.

Deliberately dependency-free and string-template based (no Jinja) to
keep this module importable with zero extra dependencies, matching the
rest of core.
"""

from __future__ import annotations

from pathlib import Path

_PYPROJECT_TEMPLATE = """\
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "{dist_name}"
version = "0.1.0"
description = "A pyagent-blueprint RuntimeAdapter for {framework_name}"
requires-python = ">=3.10"
dependencies = [
    "pyagent-blueprint>=0.1.0",
    # Add your framework's package here, e.g. "{framework_name}>=x.y.z"
]

[project.optional-dependencies]
test = ["pytest>=8.0", "pytest-asyncio>=0.23"]

[project.entry-points."pyagent_blueprint.adapters"]
{adapter_name} = "{module_name}.adapter:{class_name}"

[tool.hatch.build.targets.wheel]
packages = ["src/{module_name}"]
"""

_ADAPTER_MODULE_TEMPLATE = '''\
"""{class_name}: a pyagent-blueprint RuntimeAdapter for {framework_name}.

Fill in `compile()` and `run()` with calls into the {framework_name} SDK.
Everything else (Capability flags, diagnostics, streaming/export) is
optional — only declare a Capability if you actually implement the
corresponding method.

Acceptance bar: this adapter must pass `AdapterConformanceSuite`
(see the generated test file alongside this module) before it's
considered conformant.
"""

from __future__ import annotations

from typing import Any

from pyagent_blueprint.adapter import (
    AdapterResult,
    Capability,
    CompiledArtifact,
    RuntimeAdapter,
    UnknownWorkflowError,
)
from pyagent_blueprint.ir import BlueprintIR


class {class_name}(RuntimeAdapter):
    """TODO: describe what {framework_name} is and how workflows map onto it."""

    name = "{adapter_name}"
    # TODO: declare only the capabilities you actually implement, e.g.:
    # capabilities = Capability.STREAMING | Capability.NATIVE_TOOL_CALLING
    capabilities = Capability.NONE

    def compile(self, ir: BlueprintIR) -> CompiledArtifact:
        """Translate the framework-agnostic IR into a {framework_name}-native
        compiled object. Report any governance feature you cannot honor
        (routing, budget, sla, memory_tier, recovery, guardrails,
        checkpoints) via `CompileDiagnostic`s in the returned artifact —
        see `pyagent_blueprint.diagnostics` for the stable codes and
        `pyagent_blueprint.adapters.reference._common.diagnose_common_governance`
        for a reusable helper if you don't support any of them.
        """
        raise NotImplementedError("TODO: implement compile() for {framework_name}")

    async def run(self, artifact: CompiledArtifact, workflow: str, input_: str) -> AdapterResult:
        """Execute the given workflow. Must raise `UnknownWorkflowError`
        (not a raw KeyError/AttributeError) for an unresolvable workflow
        name."""
        raise NotImplementedError("TODO: implement run() for {framework_name}")
'''

_TEST_MODULE_TEMPLATE = '''\
"""Conformance tests for {class_name}.

This subclasses the shared `AdapterConformanceSuite` — passing this file
is the acceptance bar for shipping the adapter.
"""

from __future__ import annotations

import pytest

from pyagent_blueprint.conformance import AdapterConformanceSuite
from {module_name}.adapter import {class_name}


class Test{class_name}Conformance(AdapterConformanceSuite):
    @pytest.fixture
    def adapter(self) -> {class_name}:
        return {class_name}()
'''

_README_TEMPLATE = """\
# {dist_name}

A [pyagent-blueprint](https://pyagent.org) `RuntimeAdapter` for **{framework_name}**.

## Install

```bash
pip install -e .[test]
```

## Implement

Fill in `src/{module_name}/adapter.py`:

1. `compile(ir: BlueprintIR) -> CompiledArtifact` — translate the
   framework-agnostic IR into a {framework_name}-native compiled object.
2. `run(artifact, workflow, input_) -> AdapterResult` — execute it.

Declare only the `Capability` flags you actually implement
(`STREAMING`, `NATIVE_TOOL_CALLING`, `SYNC_EXECUTION`,
`PARTIAL_WORKFLOW_RUN`, `ROUND_TRIP`) — everything else stays optional.

## Prove it

```bash
pytest tests/
```

This runs the shared `AdapterConformanceSuite` against your adapter.
Passing it is the acceptance bar for publishing on pyagent.org.
"""


def render_adapter_template(
    framework_name: str,
    adapter_name: str | None = None,
    dist_name: str | None = None,
) -> dict[str, str]:
    """Render the file contents for a starter adapter package.

    Args:
        framework_name: Human-readable SDK name, e.g. "LangGraph".
        adapter_name: entry-point / RuntimeAdapter.name value. Defaults
            to a snake_case derivation of framework_name.
        dist_name: PyPI distribution name. Defaults to
            "pyagent-blueprint-adapter-<adapter_name-with-dashes>".

    Returns:
        Mapping of relative file path -> file content, ready to be
        written to disk.
    """
    slug = "".join(c if c.isalnum() else "_" for c in framework_name.lower()).strip("_")
    while "__" in slug:
        slug = slug.replace("__", "_")

    adapter_name = adapter_name or slug
    module_name = f"pyagent_blueprint_adapter_{slug}"
    class_name = "".join(part.capitalize() for part in slug.split("_")) + "Adapter"
    dist_name = dist_name or f"pyagent-blueprint-adapter-{slug.replace('_', '-')}"

    fmt_kwargs = {
        "framework_name": framework_name,
        "adapter_name": adapter_name,
        "module_name": module_name,
        "class_name": class_name,
        "dist_name": dist_name,
    }

    return {
        "pyproject.toml": _PYPROJECT_TEMPLATE.format(**fmt_kwargs),
        f"src/{module_name}/__init__.py": "",
        f"src/{module_name}/adapter.py": _ADAPTER_MODULE_TEMPLATE.format(**fmt_kwargs),
        f"tests/test_{slug}_adapter_conformance.py": _TEST_MODULE_TEMPLATE.format(**fmt_kwargs),
        "README.md": _README_TEMPLATE.format(**fmt_kwargs),
    }


def write_adapter_template(
    framework_name: str,
    output_dir: str | Path,
    adapter_name: str | None = None,
    dist_name: str | None = None,
) -> Path:
    """Render and write a starter adapter package to `output_dir`.

    Returns the output directory path.
    """
    files = render_adapter_template(framework_name, adapter_name, dist_name)
    out_dir = Path(output_dir)

    for rel_path, content in files.items():
        full_path = out_dir / rel_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content)

    return out_dir
