"""Tests for blueprint loader: YAML, JSON, missing file, validation error."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest
from pyagent_blueprint.loader import BlueprintLoadError, load_blueprint, load_blueprint_from_str

FIXTURES = Path(__file__).parent / "fixtures"


def test_load_yaml() -> None:
    spec = load_blueprint(FIXTURES / "customer_support.yaml")
    assert spec.metadata.name == "customer-support"
    assert "classifier" in spec.agents
    assert "support" in spec.workflows


def test_load_json() -> None:
    with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
        data = {
            "metadata": {"name": "json-test"},
            "agents": {"a": {"prompt": "test"}},
            "workflows": {"w": {"pattern": "pipeline"}},
        }
        json.dump(data, f)
        f.flush()
        spec = load_blueprint(f.name)
        assert spec.metadata.name == "json-test"


def test_load_missing_file() -> None:
    with pytest.raises(BlueprintLoadError, match="not found"):
        load_blueprint("/nonexistent/path.yaml")


def test_load_invalid_schema() -> None:
    with pytest.raises(BlueprintLoadError, match="Schema validation failed"):
        load_blueprint(FIXTURES / "invalid_blueprint.yaml")


def test_load_from_str() -> None:
    yaml_str = """
metadata:
  name: string-test
agents:
  a:
    prompt: hello
workflows:
  w:
    pattern: pipeline
"""
    spec = load_blueprint_from_str(yaml_str)
    assert spec.metadata.name == "string-test"
