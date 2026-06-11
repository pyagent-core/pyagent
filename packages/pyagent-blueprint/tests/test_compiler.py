"""Tests for BlueprintCompiler: compile to RuntimeGraph."""

from __future__ import annotations

from pathlib import Path

import pytest
from pyagent_blueprint.compiler import BlueprintCompiler, CompilationError
from pyagent_blueprint.loader import load_blueprint

FIXTURES = Path(__file__).parent / "fixtures"


def test_compile_pipeline() -> None:
    spec = load_blueprint(FIXTURES / "research_agent.yaml")
    compiler = BlueprintCompiler()
    graph = compiler.compile(spec)

    assert "research" in graph
    desc = graph.describe()
    assert "research" in desc["workflows"]


@pytest.mark.asyncio
async def test_compile_pipeline_runnable() -> None:
    spec = load_blueprint(FIXTURES / "research_agent.yaml")
    compiler = BlueprintCompiler()
    graph = compiler.compile(spec)

    result = await graph.run("research", "Explain quantum computing")
    assert isinstance(result.output, str)
    assert len(result.output) > 0


def test_compile_supervisor() -> None:
    spec = load_blueprint(FIXTURES / "customer_support.yaml")
    compiler = BlueprintCompiler()
    graph = compiler.compile(spec)

    assert "support" in graph
    assert graph.workflow_names == ["support"]


def test_compile_unknown_pattern() -> None:
    from pyagent_blueprint.schema import (
        AgentSpec,
        BlueprintSpec,
        MetadataSpec,
        WorkflowSpec,
    )

    spec = BlueprintSpec(
        metadata=MetadataSpec(name="bad"),
        agents={"a": AgentSpec(prompt="x")},
        workflows={"w": WorkflowSpec(pattern="nonexistent_pattern", agents={"a": "a"})},
    )
    compiler = BlueprintCompiler()
    with pytest.raises(CompilationError, match="Unknown pattern"):
        compiler.compile(spec)
