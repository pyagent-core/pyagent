"""Zero/stdlib-only reference adapters (Step 4a, CI-blocking genericity proof).

`SimpleLoopAdapter`, `StateMachineAdapter`, `SequentialChainAdapter`, and
`SingleAgentAdapter` all live here. They have NO external dependencies
(not even `pyagent-patterns`) and are registered as entry points so they
run through the conformance suite in core CI on every commit — that's
what makes "framework-agnostic" a tested claim rather than an assertion
(see TRANSFORMATION-PLAN.md Section 6/6a).
"""
