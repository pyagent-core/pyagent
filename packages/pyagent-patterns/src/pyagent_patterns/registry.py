"""Pattern registry: discover and instantiate patterns by name."""

from __future__ import annotations

from typing import Any

from pyagent_patterns.base import Pattern

_REGISTRY: dict[str, type[Pattern]] = {}


def register_pattern(name: str, cls: type[Pattern]) -> None:
    """Register a pattern class under a name."""
    _REGISTRY[name] = cls


def get_pattern_class(name: str) -> type[Pattern] | None:
    """Look up a pattern class by name."""
    return _REGISTRY.get(name)


def list_patterns() -> list[str]:
    """Return all registered pattern names."""
    return sorted(_REGISTRY.keys())


def _auto_register() -> None:
    """Auto-register all built-in patterns."""
    from pyagent_patterns.advanced.human_in_the_loop import HumanInTheLoop
    from pyagent_patterns.advanced.react import ReAct
    from pyagent_patterns.advanced.swarm import Swarm
    from pyagent_patterns.advanced.talker_reasoner import TalkerReasoner
    from pyagent_patterns.orchestration.fan_out_fan_in import FanOutFanIn
    from pyagent_patterns.orchestration.hierarchical import Hierarchical
    from pyagent_patterns.orchestration.orchestrator_workers import OrchestratorWorkers
    from pyagent_patterns.orchestration.pipeline import Pipeline
    from pyagent_patterns.orchestration.supervisor import Supervisor
    from pyagent_patterns.resolution.cross_reflection import CrossReflection
    from pyagent_patterns.resolution.debate import Debate
    from pyagent_patterns.resolution.evaluator_optimizer import EvaluatorOptimizer
    from pyagent_patterns.resolution.self_reflection import SelfReflection
    from pyagent_patterns.resolution.voting import Voting
    from pyagent_patterns.structural.blackboard import Blackboard
    from pyagent_patterns.structural.layered import Layered
    from pyagent_patterns.structural.role_based import RoleBased
    from pyagent_patterns.structural.topology import Topology

    for name, cls in [
        ("supervisor", Supervisor),
        ("pipeline", Pipeline),
        ("fan_out_fan_in", FanOutFanIn),
        ("hierarchical", Hierarchical),
        ("orchestrator_workers", OrchestratorWorkers),
        ("self_reflection", SelfReflection),
        ("cross_reflection", CrossReflection),
        ("debate", Debate),
        ("voting", Voting),
        ("evaluator_optimizer", EvaluatorOptimizer),
        ("role_based", RoleBased),
        ("layered", Layered),
        ("topology", Topology),
        ("blackboard", Blackboard),
        ("talker_reasoner", TalkerReasoner),
        ("swarm", Swarm),
        ("human_in_the_loop", HumanInTheLoop),
        ("react", ReAct),
    ]:
        register_pattern(name, cls)


_auto_register()
