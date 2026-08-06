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
    result = runner.invoke(
        cli, ["render", str(FIXTURES / "customer_support.yaml"), "--format", "markdown"]
    )
    assert result.exit_code == 0
    assert "# customer-support" in result.output


def test_generate() -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "generate",
            "--pattern",
            "pipeline",
            "--agents",
            "researcher,reviewer",
            "--name",
            "test-bp",
        ],
    )
    assert result.exit_code == 0
    assert "pipeline" in result.output
    assert "researcher" in result.output


def test_generate_unknown_pattern() -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "generate",
            "--pattern",
            "nonexistent",
            "--agents",
            "a,b",
        ],
    )
    assert result.exit_code != 0


def test_package_cmd(tmp_path: Path) -> None:
    runner = CliRunner()
    output_dir = tmp_path / "dist"
    result = runner.invoke(
        cli,
        ["package", str(FIXTURES / "packaged_research_agent.yaml"), "-o", str(output_dir)],
    )
    assert result.exit_code == 0, result.output
    assert "Packaged Agent Unit" in result.output
    archives = list(output_dir.glob("*.agentunit.zip"))
    assert len(archives) == 1


def test_package_cmd_missing_package_block() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["package", str(FIXTURES / "research_agent.yaml")])
    assert result.exit_code != 0
    assert "Packaging error" in result.output


def test_adapters_cmd() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["adapters"])
    assert result.exit_code == 0
    assert "single_agent" in result.output


def test_adapter_template_cmd(tmp_path: Path) -> None:
    runner = CliRunner()
    output_dir = tmp_path / "scaffold"
    result = runner.invoke(
        cli,
        ["adapter-template", "--framework", "CrewAI", "-o", str(output_dir)],
    )
    assert result.exit_code == 0, result.output
    assert (output_dir / "pyproject.toml").exists()
    assert (output_dir / "src" / "pyagent_blueprint_adapter_crewai" / "adapter.py").exists()
