"""Tests for CLI: smoke tests via Click's CliRunner."""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from pyagent_blueprint.cli import cli


FIXTURES = Path(__file__).parent / "fixtures"


def test_validate_valid() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["validate", str(FIXTURES / "customer_support.yaml")])
    assert result.exit_code == 0
    assert "valid" in result.output.lower() or "no issues" in result.output.lower()


def test_validate_invalid() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["validate", str(FIXTURES / "invalid_blueprint.yaml")])
    # Should fail because metadata is missing
    assert result.exit_code != 0


def test_compile_cmd() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["compile", str(FIXTURES / "research_agent.yaml")])
    assert result.exit_code == 0
    assert "research" in result.output


def test_render_mermaid() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["render", str(FIXTURES / "customer_support.yaml")])
    assert result.exit_code == 0
    assert "graph TD" in result.output


def test_render_markdown() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["render", str(FIXTURES / "customer_support.yaml"), "--format", "markdown"])
    assert result.exit_code == 0
    assert "# customer-support" in result.output


def test_generate() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, [
        "generate",
        "--pattern", "pipeline",
        "--agents", "researcher,reviewer",
        "--name", "test-bp",
    ])
    assert result.exit_code == 0
    assert "pipeline" in result.output
    assert "researcher" in result.output


def test_generate_unknown_pattern() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, [
        "generate",
        "--pattern", "nonexistent",
        "--agents", "a,b",
    ])
    assert result.exit_code != 0
