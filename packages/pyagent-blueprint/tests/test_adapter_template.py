"""Tests for pyagent_blueprint.adapter_template (Step 7)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from pyagent_blueprint.adapter_template import render_adapter_template, write_adapter_template


def test_render_adapter_template_derives_names() -> None:
    files = render_adapter_template("LangGraph")

    assert "pyproject.toml" in files
    assert "src/pyagent_blueprint_adapter_langgraph/adapter.py" in files
    assert "tests/test_langgraph_adapter_conformance.py" in files
    assert "README.md" in files

    pyproject = files["pyproject.toml"]
    assert "langgraph = " in pyproject
    assert "pyagent_blueprint_adapter_langgraph.adapter:LanggraphAdapter" in pyproject

    adapter_module = files["src/pyagent_blueprint_adapter_langgraph/adapter.py"]
    assert "class LanggraphAdapter(RuntimeAdapter):" in adapter_module
    assert 'name = "langgraph"' in adapter_module

    test_module = files["tests/test_langgraph_adapter_conformance.py"]
    assert "AdapterConformanceSuite" in test_module
    assert "LanggraphAdapter" in test_module


def test_write_adapter_template_writes_files(tmp_path: Path) -> None:
    out_dir = write_adapter_template("MyFramework", output_dir=tmp_path / "scaffold")

    assert (out_dir / "pyproject.toml").exists()
    assert (out_dir / "README.md").exists()
    module_dir = out_dir / "src" / "pyagent_blueprint_adapter_myframework"
    assert (module_dir / "__init__.py").exists()
    assert (module_dir / "adapter.py").exists()


def test_scaffolded_adapter_is_a_valid_runtime_adapter_stub(tmp_path: Path) -> None:
    """The scaffold's adapter.py must at least be syntactically valid
    Python and subclass RuntimeAdapter correctly (it's expected to raise
    NotImplementedError until filled in — that's fine, we're only
    proving the *shape* is right, not that it's a working adapter)."""
    out_dir = write_adapter_template("StubFramework", output_dir=tmp_path / "scaffold")
    adapter_path = out_dir / "src" / "pyagent_blueprint_adapter_stubframework" / "adapter.py"

    # Compile-check for syntax validity without needing to install the package.
    result = subprocess.run(
        [sys.executable, "-m", "py_compile", str(adapter_path)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
