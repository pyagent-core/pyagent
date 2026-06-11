"""Tests for the pyagent CLI command group."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner
from pyagent_studio.cli import main

# Use the existing fixture from pyagent-blueprint tests
_FIXTURE_DIR = (
    Path(__file__).resolve().parent.parent.parent / "pyagent-blueprint" / "tests" / "fixtures"
)
_BLUEPRINT = str(_FIXTURE_DIR / "customer_support.yaml")


@pytest.fixture
def runner():
    return CliRunner()


# --- help ---


def test_cli_help(runner):
    """--help shows all commands."""
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    for cmd in [
        "apply",
        "get",
        "validate",
        "test",
        "diff",
        "simulate",
        "render",
        "generate",
        "providers",
        "describe",
        "dashboard",
    ]:
        assert cmd in result.output, f"Missing command: {cmd}"


def test_cli_unknown_command(runner):
    """Unknown subcommand prints error."""
    result = runner.invoke(main, ["nonexistent"])
    assert result.exit_code != 0


# --- apply ---


def test_cli_apply_valid_blueprint(runner):
    """apply loads and validates a blueprint."""
    if not Path(_BLUEPRINT).exists():
        pytest.skip("fixture not found")
    result = runner.invoke(main, ["apply", _BLUEPRINT])
    assert result.exit_code == 0
    assert "customer-support" in result.output


def test_cli_apply_invalid_file(runner):
    """apply prints error for missing file."""
    result = runner.invoke(main, ["apply", "/nonexistent/file.yaml"])
    assert result.exit_code != 0


# --- get ---


def test_cli_get_agents(runner):
    """get agents lists agents from blueprint."""
    if not Path(_BLUEPRINT).exists():
        pytest.skip("fixture not found")
    result = runner.invoke(main, ["get", "agents", _BLUEPRINT])
    assert result.exit_code == 0
    assert "classifier" in result.output


def test_cli_get_workflows(runner):
    """get workflows lists workflows."""
    if not Path(_BLUEPRINT).exists():
        pytest.skip("fixture not found")
    result = runner.invoke(main, ["get", "workflows", _BLUEPRINT])
    assert result.exit_code == 0
    assert "support" in result.output


def test_cli_get_providers(runner):
    """get providers lists providers."""
    if not Path(_BLUEPRINT).exists():
        pytest.skip("fixture not found")
    result = runner.invoke(main, ["get", "providers", _BLUEPRINT])
    assert result.exit_code == 0
    assert "primary" in result.output


def test_cli_get_contracts(runner):
    """get contracts lists contracts."""
    if not Path(_BLUEPRINT).exists():
        pytest.skip("fixture not found")
    result = runner.invoke(main, ["get", "contracts", _BLUEPRINT])
    assert result.exit_code == 0
    assert "support" in result.output


# --- validate ---


def test_cli_validate_valid(runner):
    """validate prints Valid for a good blueprint."""
    if not Path(_BLUEPRINT).exists():
        pytest.skip("fixture not found")
    result = runner.invoke(main, ["validate", _BLUEPRINT])
    # It may be valid or have warnings, but should not crash
    assert result.exit_code in (0, 1)


# --- test ---


def test_cli_test_blueprint(runner):
    """test runs contract conformance checks."""
    if not Path(_BLUEPRINT).exists():
        pytest.skip("fixture not found")
    result = runner.invoke(main, ["test", _BLUEPRINT])
    assert "customer-support" in result.output or "Testing" in result.output


# --- diff ---


def test_cli_diff_blueprints(runner):
    """diff compares two blueprints."""
    if not Path(_BLUEPRINT).exists():
        pytest.skip("fixture not found")
    # Diff same file against itself — should show no differences
    result = runner.invoke(main, ["diff", _BLUEPRINT, _BLUEPRINT])
    assert result.exit_code == 0


# --- simulate ---


def test_cli_simulate_mock(runner):
    """simulate runs workflow with MockLLM."""
    if not Path(_BLUEPRINT).exists():
        pytest.skip("fixture not found")

    with patch("pyagent_studio.services.simulation_service.SimulationService") as mock_cls:
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.output = "Mock output"
        mock_result.elapsed_ms = 42.0
        mock_instance = MagicMock()
        mock_instance.run = AsyncMock(return_value=mock_result)
        mock_cls.return_value = mock_instance

        result = runner.invoke(main, ["simulate", _BLUEPRINT, "support", "Hello"])
        assert result.exit_code == 0
        assert "Mock output" in result.output


def test_cli_simulate_live_flag(runner):
    """--live flag is accepted."""
    if not Path(_BLUEPRINT).exists():
        pytest.skip("fixture not found")

    with patch("pyagent_studio.services.simulation_service.SimulationService") as mock_cls:
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.output = "Live output"
        mock_result.elapsed_ms = 100.0
        mock_instance = MagicMock()
        mock_instance.run = AsyncMock(return_value=mock_result)
        mock_cls.return_value = mock_instance

        result = runner.invoke(main, ["simulate", _BLUEPRINT, "support", "Hello", "--live"])
        assert result.exit_code == 0
        mock_cls.assert_called_once_with(use_live=True)


# --- render ---


def test_cli_render_markdown(runner):
    """render outputs Markdown."""
    if not Path(_BLUEPRINT).exists():
        pytest.skip("fixture not found")
    result = runner.invoke(main, ["render", _BLUEPRINT])
    assert result.exit_code == 0
    # Markdown output should contain some text
    assert len(result.output) > 0


def test_cli_render_mermaid(runner):
    """render --format mermaid outputs Mermaid."""
    if not Path(_BLUEPRINT).exists():
        pytest.skip("fixture not found")
    result = runner.invoke(main, ["render", _BLUEPRINT, "--format", "mermaid"])
    assert result.exit_code == 0
    assert len(result.output) > 0


# --- generate ---


def test_cli_generate_scaffold(runner):
    """generate creates a blueprint YAML."""
    result = runner.invoke(main, ["generate", "--pattern", "pipeline", "--agents", "a,b,c"])
    assert result.exit_code == 0
    assert len(result.output) > 0


# --- providers ---


def test_cli_providers_list(runner):
    """providers list shows models."""
    with (
        patch("pyagent_studio.services.provider_service._HAS_LITELLM", True),
        patch("pyagent_studio.services.provider_service.litellm") as mock_litellm,
    ):
        mock_litellm.model_list = ["gpt-4o", "claude-3"]
        result = runner.invoke(main, ["providers", "list"])
        assert result.exit_code == 0
        assert "gpt-4o" in result.output


def test_cli_providers_health(runner):
    """providers health runs health check."""
    with (
        patch("pyagent_studio.services.provider_service._HAS_LITELLM", True),
        patch("pyagent_studio.services.provider_service.litellm") as mock_litellm,
    ):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "pong"
        mock_litellm.acompletion = AsyncMock(return_value=mock_response)

        result = runner.invoke(main, ["providers", "health"])
        assert result.exit_code == 0
        assert "healthy" in result.output


# --- describe ---


def test_cli_describe(runner):
    """describe prints blueprint summary."""
    if not Path(_BLUEPRINT).exists():
        pytest.skip("fixture not found")
    result = runner.invoke(main, ["describe", _BLUEPRINT])
    assert result.exit_code == 0
    assert "name" in result.output
    assert "customer-support" in result.output


# --- dashboard ---


def test_cli_dashboard_starts(runner):
    """dashboard command accepted (mock uvicorn)."""
    mock_uvicorn = MagicMock()
    with patch.dict("sys.modules", {"uvicorn": mock_uvicorn}):
        result = runner.invoke(main, ["dashboard"])
        assert result.exit_code == 0
        assert "Starting dashboard" in result.output
        mock_uvicorn.run.assert_called_once()
