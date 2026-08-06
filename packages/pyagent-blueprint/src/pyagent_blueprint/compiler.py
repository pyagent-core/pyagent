"""BlueprintCompiler: DEPRECATED thin shim over `PyAgentAdapter`.

Kept for backward compatibility only. New code should use
`pyagent_blueprint.adapter.RuntimeAdapter` implementations (e.g.
`pyagent_blueprint.adapters.pyagent_adapter.PyAgentAdapter`) directly, or
go through `AdapterRegistry`.

This module itself has ZERO import on `pyagent_patterns` — all runtime
coupling lives in `adapters/pyagent_adapter.py`, enforced by
`tests/test_no_runtime_imports.py`.
"""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING, Any

from pyagent_blueprint.ir import BlueprintIR

if TYPE_CHECKING:
    from pyagent_blueprint.runtime import RuntimeGraph
    from pyagent_blueprint.schema.spec import BlueprintSpec


class CompilationError(Exception):
    """Raised when a blueprint cannot be compiled.

    Preserved for backward compatibility — wraps
    `adapters.pyagent_adapter.PyAgentCompilationError`.
    """


class BlueprintCompiler:
    """DEPRECATED: use `PyAgentAdapter` (or any `RuntimeAdapter`) directly.

    Compile a BlueprintSpec into a RuntimeGraph, delegating to
    `pyagent_blueprint.adapters.pyagent_adapter.PyAgentAdapter`.

    Args:
        provider_registry: Optional ``ProviderRegistry`` for real providers.
            If ``None``, uses ``MockLLM`` for all providers.
    """

    def __init__(self, provider_registry: Any = None) -> None:
        warnings.warn(
            "BlueprintCompiler is deprecated; use "
            "pyagent_blueprint.adapters.pyagent_adapter.PyAgentAdapter "
            "(or any RuntimeAdapter) directly. This shim will be removed "
            "in a future major version.",
            DeprecationWarning,
            stacklevel=2,
        )
        self._provider_registry = provider_registry

    def compile(self, spec: BlueprintSpec) -> RuntimeGraph:
        """Compile a blueprint spec into a runnable RuntimeGraph.

        Args:
            spec: Validated ``BlueprintSpec``.

        Returns:
            ``RuntimeGraph`` ready to execute.

        Raises:
            CompilationError: If the spec references unknown patterns or agents.
        """
        from pyagent_blueprint.adapters.pyagent_adapter import (
            PyAgentAdapter,
            PyAgentCompilationError,
        )

        ir = BlueprintIR.from_spec(spec)
        adapter = PyAgentAdapter(provider_registry=self._provider_registry)
        try:
            compiled = adapter.compile(ir)
        except PyAgentCompilationError as exc:
            raise CompilationError(str(exc)) from exc
        return compiled.handle
