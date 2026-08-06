"""Tests for pyagent_blueprint.packaging — Agent Unit packaging (Step 6)."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from pyagent_blueprint.loader import load_blueprint
from pyagent_blueprint.packaging import (
    AgentUnitMetadata,
    PackagingError,
    build_metadata,
    package_blueprint,
)

FIXTURES = Path(__file__).parent / "fixtures"


def test_build_metadata_requires_package_block() -> None:
    spec = load_blueprint(FIXTURES / "research_agent.yaml")
    with pytest.raises(PackagingError, match="no 'package:' block"):
        build_metadata(spec, "irrelevant")


def test_build_metadata_success() -> None:
    spec = load_blueprint(FIXTURES / "packaged_research_agent.yaml")
    raw = (FIXTURES / "packaged_research_agent.yaml").read_text()
    metadata = build_metadata(spec, raw)

    assert isinstance(metadata, AgentUnitMetadata)
    assert metadata.name == "research-agent-unit"
    assert metadata.version == "1.0.0"
    assert metadata.runtime == "single_agent"
    assert len(metadata.spec_sha256) == 64  # sha256 hex digest length


def test_build_metadata_rejects_unknown_runtime() -> None:
    spec = load_blueprint(FIXTURES / "packaged_research_agent.yaml")
    spec = spec.model_copy(update={"package": spec.package.model_copy(update={"runtime": "nonexistent_adapter_xyz"})})
    raw = (FIXTURES / "packaged_research_agent.yaml").read_text()

    with pytest.raises(PackagingError, match="does not match any discoverable adapter"):
        build_metadata(spec, raw)


def test_package_blueprint_writes_archive(tmp_path: Path) -> None:
    spec = load_blueprint(FIXTURES / "packaged_research_agent.yaml")
    raw = (FIXTURES / "packaged_research_agent.yaml").read_text()

    archive_path = package_blueprint(
        spec, raw, "packaged_research_agent.yaml", output_dir=tmp_path
    )

    assert archive_path.exists()
    assert archive_path.name == "research-agent-unit-1.0.0.agentunit.zip"

    with zipfile.ZipFile(archive_path) as zf:
        names = zf.namelist()
        assert "unit.json" in names
        assert "packaged_research_agent.yaml" in names

        manifest = json.loads(zf.read("unit.json"))
        assert manifest["name"] == "research-agent-unit"
        assert manifest["runtime"] == "single_agent"
        assert manifest["unit_schema_version"] == "1.0"
