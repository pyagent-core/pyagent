"""Reference `RuntimeAdapter` implementations.

`pyagent_adapter.py` wraps our own native runtime (`pyagent-patterns`).
Additional zero/stdlib-dependency reference adapters
(`SimpleLoopAdapter`, `StateMachineAdapter`, `SequentialChainAdapter`,
`SingleAgentAdapter`) are added incrementally in follow-on PRs (Step 4a).

This subpackage is the ONLY place `pyagent_blueprint` may import an
agent-execution framework. `pyagent_blueprint` core (schema, ir, loader,
validator, differ, renderer, adapter.py, conformance.py) has zero such
imports — enforced by `tests/test_no_runtime_imports.py`.
"""
