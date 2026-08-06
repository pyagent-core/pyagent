"""Pattern-instantiation coverage for PyAgentAdapter.

The conformance suite proves the RuntimeAdapter contract holds across
adapters; these tests prove PyAgentAdapter._instantiate_pattern actually
builds a runnable native Pattern for every pattern shape whose blueprint
wiring isn't a flat agent-ref (hierarchical's Team, blackboard's
BlackboardAgent, layered's Layer, fan_out_fan_in/voting/debate's
non-`agents=` constructor kwargs, and the StrEnum-typed voting.strategy /
topology.topology config values) — regression coverage for bugs found
while wiring the examples/cookbook blueprints correctly.
"""

from __future__ import annotations

import pytest
from pyagent_blueprint.adapters.pyagent_adapter import PyAgentAdapter
from pyagent_blueprint.ir import BlueprintIR
from pyagent_blueprint.loader import load_blueprint_from_str

CASES = {
    "hierarchical": (
        """
api_version: pyagent/v1
metadata: {name: t-hier, version: 1.0.0}
providers: {p: {model: gpt-4o-mini}}
agents:
  manager: {provider: p, prompt: "manage"}
  research_lead: {provider: p, prompt: "lead research"}
  researcher_a: {provider: p, prompt: "research a"}
  risk_lead: {provider: p, prompt: "lead risk"}
  risk_analyst: {provider: p, prompt: "analyze risk"}
workflows:
  brief:
    pattern: hierarchical
    agents:
      manager: manager
      teams:
        - name: Research
          lead: research_lead
          workers: [researcher_a]
        - name: Risk
          lead: risk_lead
          workers: [risk_analyst]
""",
        "brief",
    ),
    "orchestrator_workers": (
        """
api_version: pyagent/v1
metadata: {name: t-ow, version: 1.0.0}
providers: {p: {model: gpt-4o-mini}}
agents:
  orch: {provider: p, prompt: "orchestrate"}
  w1: {provider: p, prompt: "worker 1"}
  w2: {provider: p, prompt: "worker 2"}
workflows:
  analyze:
    pattern: orchestrator_workers
    agents:
      orchestrator: orch
      workers: [w1, w2]
""",
        "analyze",
    ),
    "blackboard": (
        """
api_version: pyagent/v1
metadata: {name: t-bb, version: 1.0.0}
providers: {p: {model: gpt-4o-mini}}
agents:
  a1: {provider: p, prompt: "agent 1"}
  a2: {provider: p, prompt: "agent 2"}
workflows:
  simulate:
    pattern: blackboard
    agents:
      agents:
        - agent: a1
          reads: [task]
          writes: [world_state]
        - agent: a2
          reads: [world_state]
          writes: [npc_actions]
    config:
      rounds: 1
""",
        "simulate",
    ),
    "layered": (
        """
api_version: pyagent/v1
metadata: {name: t-layered, version: 1.0.0}
providers: {p: {model: gpt-4o-mini}}
agents:
  data1: {provider: p, prompt: "gather data"}
  analyst1: {provider: p, prompt: "analyze"}
workflows:
  value:
    pattern: layered
    agents:
      layers:
        - name: Data
          agents: [data1]
        - name: Analysis
          agents: [analyst1]
""",
        "value",
    ),
    "fan_out_fan_in": (
        """
api_version: pyagent/v1
metadata: {name: t-fofi, version: 1.0.0}
providers: {p: {model: gpt-4o-mini}}
agents:
  a1: {provider: p, prompt: "analyst 1"}
  a2: {provider: p, prompt: "analyst 2"}
  agg: {provider: p, prompt: "aggregate"}
workflows:
  generate:
    pattern: fan_out_fan_in
    agents:
      agents: [a1, a2]
      aggregator: agg
""",
        "generate",
    ),
    "voting": (
        """
api_version: pyagent/v1
metadata: {name: t-vote, version: 1.0.0}
providers: {p: {model: gpt-4o-mini}}
agents:
  v1: {provider: p, prompt: "vote 1"}
  v2: {provider: p, prompt: "vote 2"}
  v3: {provider: p, prompt: "vote 3"}
workflows:
  grade:
    pattern: voting
    agents:
      voters: [v1, v2, v3]
    config:
      strategy: majority
""",
        "grade",
    ),
    "debate": (
        """
api_version: pyagent/v1
metadata: {name: t-debate, version: 1.0.0}
providers: {p: {model: gpt-4o-mini}}
agents:
  buy: {provider: p, prompt: "argue buy"}
  sell: {provider: p, prompt: "argue sell"}
  judge: {provider: p, prompt: "judge"}
workflows:
  underwrite:
    pattern: debate
    agents:
      debaters: [buy, sell]
      judge: judge
    config:
      rounds: 2
""",
        "underwrite",
    ),
    "topology": (
        """
api_version: pyagent/v1
metadata: {name: t-topo, version: 1.0.0}
providers: {p: {model: gpt-4o-mini}}
agents:
  a1: {provider: p, prompt: "reviewer 1"}
  a2: {provider: p, prompt: "reviewer 2"}
workflows:
  review:
    pattern: topology
    agents:
      agents: [a1, a2]
    config:
      topology: chain
""",
        "review",
    ),
}


@pytest.mark.parametrize("pattern_name", sorted(CASES))
@pytest.mark.asyncio
async def test_pattern_compiles_and_runs(pattern_name: str) -> None:
    yaml_str, workflow_name = CASES[pattern_name]
    spec = load_blueprint_from_str(yaml_str)
    ir = BlueprintIR.from_spec(spec)
    adapter = PyAgentAdapter()
    artifact = adapter.compile(ir)
    result = await adapter.run(artifact, workflow=workflow_name, input_="test task")
    assert result.output
