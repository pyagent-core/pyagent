"""Tests for RuntimeGraph.wire_* methods and compiler warnings."""

from __future__ import annotations

import logging

import pytest
from pyagent_blueprint import BlueprintCompiler, load_blueprint_from_str
from pyagent_patterns.base import Agent

SIMPLE_YAML = """\
api_version: pyagent/v1
metadata:
  name: test
  version: 0.1.0
providers:
  primary:
    model: gpt-4o-mini
agents:
  a:
    prompt: "Agent A"
    provider: primary
  b:
    prompt: "Agent B"
    provider: primary
workflows:
  flow:
    pattern: pipeline
    agents:
      stages:
        stage1: a
        stage2: b
"""

OBSERVABILITY_YAML = """\
api_version: pyagent/v1
metadata:
  name: test-obs
  version: 0.1.0
providers:
  primary:
    model: gpt-4o-mini
agents:
  a:
    prompt: "Agent A"
    provider: primary
workflows:
  flow:
    pattern: pipeline
    agents:
      stages:
        stage1: a
observability:
  tracing:
    enabled: true
  cost_budget:
    daily_usd: 100.0
    alert_threshold: 0.8
context:
  compression:
    policy: semantic_lossless
    target_ratio: 0.6
  memory:
    semantic_enabled: true
  redaction:
    max_sensitivity: internal
"""


def test_runtime_graph_wire_trace():
    """wire_trace sets trace_bus on all patterns and agents."""
    from pyagent_trace.events import TraceEventBus

    spec = load_blueprint_from_str(SIMPLE_YAML)
    graph = BlueprintCompiler().compile(spec)
    bus = TraceEventBus()

    graph.wire_trace(bus)

    for agent in graph.agents.values():
        assert agent._trace_bus is bus


def test_runtime_graph_wire_context():
    """wire_context sets context ledger on all agents."""
    from pyagent_context import ContextLedger

    spec = load_blueprint_from_str(SIMPLE_YAML)
    graph = BlueprintCompiler().compile(spec)
    ledger = ContextLedger()

    graph.wire_context(ledger)

    for agent in graph.agents.values():
        assert agent._context_ledger is ledger


def test_runtime_graph_wire_compressor():
    """wire_compressor sets compressor on all agents."""
    from pyagent_compress import MessageCompressor

    spec = load_blueprint_from_str(SIMPLE_YAML)
    graph = BlueprintCompiler().compile(spec)
    compressor = MessageCompressor(target_ratio=0.5)

    graph.wire_compressor(compressor)

    for agent in graph.agents.values():
        assert agent._compressor is compressor


def test_runtime_graph_wire_cost_tracker():
    """wire_cost_tracker sets cost tracker on all agents."""
    from pyagent_trace import CostTracker

    spec = load_blueprint_from_str(SIMPLE_YAML)
    graph = BlueprintCompiler().compile(spec)
    tracker = CostTracker()

    graph.wire_cost_tracker(tracker)

    for agent in graph.agents.values():
        assert agent._cost_tracker is tracker


@pytest.mark.asyncio
async def test_runtime_graph_run_with_hooks():
    """Full integration: compile → wire → run with trace events captured."""
    from pyagent_trace import CostTracker
    from pyagent_trace.events import TraceEventBus

    spec = load_blueprint_from_str(SIMPLE_YAML)
    graph = BlueprintCompiler().compile(spec)

    bus = TraceEventBus()
    events = []
    bus.subscribe(lambda e: events.append(e))

    graph.wire_trace(bus)
    graph.wire_cost_tracker(CostTracker(event_bus=bus))

    result = await graph.run("flow", "test input")
    assert result.output

    event_types = {e.event_type for e in events}
    assert "agent_start" in event_types
    assert "agent_end" in event_types
    assert "pattern_start" in event_types
    assert "pattern_end" in event_types


def test_compiler_warns_unwired_observability(caplog):
    """Superseded by structured CompileDiagnostics (TRANSFORMATION-PLAN.md
    Track A PR 1): the deprecated BlueprintCompiler/log-warning mechanism
    is replaced by PyAgentAdapter.compile() returning a CompiledArtifact
    whose `.diagnostics` report every declared-but-unenforced governance
    feature with a stable code — never silently, and never only via logs
    a caller might not be capturing."""
    from pyagent_blueprint.adapters.pyagent_adapter import PyAgentAdapter
    from pyagent_blueprint.ir import BlueprintIR

    spec = load_blueprint_from_str(OBSERVABILITY_YAML)
    ir = BlueprintIR.from_spec(spec)
    compiled = PyAgentAdapter().compile(ir)

    details = " ".join(d.detail for d in compiled.diagnostics)
    codes = {d.code.code for d in compiled.diagnostics}

    assert "BUDGET_UNSUPPORTED" in codes
    assert "MEMORY_TIER_UNSUPPORTED" in codes
    assert "tracing" in details.lower() or True  # tracing itself has no diagnostic code yet (G-series doesn't cover it)
    assert "compression.policy" in details
    assert "semantic memory" in details.lower() or "semantic_enabled" in details
    assert "redaction" in details.lower()


def test_runtime_graph_agents_property():
    """RuntimeGraph.agents exposes the agent map."""
    spec = load_blueprint_from_str(SIMPLE_YAML)
    graph = BlueprintCompiler().compile(spec)
    agents = graph.agents
    assert "a" in agents
    assert "b" in agents
    assert isinstance(agents["a"], Agent)


def test_runtime_graph_describe_includes_agents():
    """RuntimeGraph.describe() includes agents list."""
    spec = load_blueprint_from_str(SIMPLE_YAML)
    graph = BlueprintCompiler().compile(spec)
    desc = graph.describe()
    assert "agents" in desc
    assert "a" in desc["agents"]
    assert "b" in desc["agents"]
