"""Tests for BlueprintRenderer: Mermaid and Markdown output."""

from __future__ import annotations

from pathlib import Path

from pyagent_blueprint.loader import load_blueprint
from pyagent_blueprint.renderer import BlueprintRenderer

FIXTURES = Path(__file__).parent / "fixtures"


def test_mermaid_contains_nodes() -> None:
    spec = load_blueprint(FIXTURES / "customer_support.yaml")
    renderer = BlueprintRenderer()
    mermaid = renderer.to_mermaid(spec)

    assert "graph TD" in mermaid
    assert "classifier" in mermaid
    assert "billing" in mermaid
    assert "tech" in mermaid


def test_mermaid_contains_edges() -> None:
    spec = load_blueprint(FIXTURES / "customer_support.yaml")
    renderer = BlueprintRenderer()
    mermaid = renderer.to_mermaid(spec)

    # Supervisor edges: classifier → billing, classifier → tech
    assert "classifier" in mermaid and "billing" in mermaid


def test_markdown_contains_sections() -> None:
    spec = load_blueprint(FIXTURES / "customer_support.yaml")
    renderer = BlueprintRenderer()
    md = renderer.to_markdown(spec)

    assert "# customer-support" in md
    assert "## Providers" in md
    assert "## Agents" in md
    assert "## Workflows" in md
    assert "## Architecture Diagram" in md
    assert "```mermaid" in md


def test_markdown_pipeline() -> None:
    spec = load_blueprint(FIXTURES / "research_agent.yaml")
    renderer = BlueprintRenderer()
    md = renderer.to_markdown(spec)

    assert "research-agent" in md
    assert "researcher" in md
    assert "reviewer" in md
