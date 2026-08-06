"""RuntimeAdapter contract: the framework-agnostic execution boundary.

`pyagent_blueprint` core (schema, ir, loader, validator, differ, renderer)
has ZERO imports on any agent-execution framework. Adapters are the only
place `pyagent_patterns`, `langgraph`, `crewai`, etc. may be imported, and
they're discovered via entry points — core never imports an adapter
package directly.

Design constraints (do not violate when adding new adapters):
- `compile()` returns `Any`, opaque to core.
- `run()` is always awaitable from the caller's perspective, even for
  natively-sync SDKs (the adapter wraps its own sync call internally).
- Streaming, native tool-calling, partial-workflow execution, and
  round-trip export/import are `Capability` flags, never required methods.
- `compile()` may return `CompileDiagnostic`s alongside the compiled
  object — every governance feature declared in the blueprint (routing,
  budget, SLA, memory tier, recovery, guardrails, checkpoints) must be
  either honored or reported via a stable `diagnostics.py` code. Silent
  drops are a contract violation.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Flag, auto
from typing import TYPE_CHECKING, Any, AsyncIterator

from pyagent_blueprint.diagnostics import DiagnosticCode

if TYPE_CHECKING:
    from pyagent_blueprint.ir import BlueprintIR


class Capability(Flag):
    """Optional features an adapter may or may not support.

    Core only ever requires COMPILE + RUN (i.e. the two abstract methods
    below). Everything else is negotiated at runtime via these flags so
    the contract never assumes a graph, async streaming, or native
    tool-calling exists.
    """

    NONE = 0
    STREAMING = auto()
    NATIVE_TOOL_CALLING = auto()
    SYNC_EXECUTION = auto()  # some SDKs are sync-only
    PARTIAL_WORKFLOW_RUN = auto()  # can run a subset of a workflow (debugging)
    ROUND_TRIP = auto()  # can export back to a BlueprintIR losslessly for shared constructs


@dataclass(frozen=True)
class CompileDiagnostic:
    """A single structured diagnostic emitted during `compile()`.

    Attributes:
        code: A stable `DiagnosticCode` from `diagnostics.py`.
        path: Dotted path into the blueprint that triggered this
            diagnostic, e.g. ``"workflows.support.recovery"``.
        detail: Adapter-specific human-readable detail.
    """

    code: DiagnosticCode
    path: str
    detail: str = ""


@dataclass
class CompiledArtifact:
    """Result of `compile()`: the opaque native handle plus diagnostics.

    Attributes:
        handle: Opaque, framework-native compiled object. Core never
            inspects this — that's the whole point of the abstraction.
        diagnostics: Every governance feature the blueprint declared that
            this adapter could NOT honor, as structured diagnostics.
            Empty means every declared feature was either honored or not
            applicable to this blueprint.
        intent: Optional map of workflow name -> original pattern name,
            preserved so pattern intent survives even when an adapter
            lowers a named pattern (e.g. "debate") to a generic graph.
    """

    handle: Any
    diagnostics: list[CompileDiagnostic] = field(default_factory=list)
    intent: dict[str, str] = field(default_factory=dict)


class AdapterResult:
    """Normalized result envelope.

    Every adapter must map its native return shape into this, so callers
    never branch on adapter identity (e.g. never special-case "if adapter
    is LangGraph, read `.raw['messages'][-1]`").
    """

    def __init__(self, output: Any, raw: Any = None, usage: dict[str, Any] | None = None) -> None:
        self.output = output  # the primary answer, always present
        self.raw = raw  # adapter-native object, for advanced users
        self.usage = usage or {}  # tokens/cost if the adapter can report it

    def __repr__(self) -> str:  # pragma: no cover - debugging aid only
        return f"AdapterResult(output={self.output!r}, usage={self.usage!r})"


class UnknownWorkflowError(Exception):
    """Raised by `RuntimeAdapter.run()`/`stream()` for an unresolvable workflow name.

    Adapters MUST raise this (not let an internal AttributeError/KeyError
    leak through) so callers get one documented, catchable error type
    regardless of which adapter is installed.
    """


class RuntimeAdapter(ABC):
    """Compiles a framework-agnostic `BlueprintIR` into a runnable object
    native to a specific agent framework, and executes it.

    Deliberately minimal: only `compile` and `run` are required. This is
    the lowest common denominator across graph-based (LangGraph),
    turn-based (AutoGen), role-based (CrewAI), handoff-based (OpenAI
    Agents SDK), event-driven (Semantic Kernel), and hand-rolled loop
    runtimes.
    """

    name: str
    capabilities: Capability = Capability.NONE

    @abstractmethod
    def compile(self, ir: BlueprintIR) -> CompiledArtifact:
        """Compile a `BlueprintIR` into a `CompiledArtifact`.

        Must report every governance feature it cannot honor via
        `CompiledArtifact.diagnostics` — never drop one silently.
        """

    @abstractmethod
    async def run(
        self, compiled: CompiledArtifact, workflow: str, input_: str, **kwargs: Any
    ) -> AdapterResult:
        """Execute a compiled workflow.

        Adapters that are natively sync (`Capability.SYNC_EXECUTION`) wrap
        their own sync call internally (e.g. via `asyncio.to_thread`) —
        callers of `RuntimeAdapter` always await, even for sync-native SDKs.

        Raises:
            UnknownWorkflowError: If `workflow` doesn't exist in `compiled`.
        """

    # -- Optional capability-gated methods (default: not implemented) --

    async def stream(
        self, compiled: CompiledArtifact, workflow: str, input_: str, **kwargs: Any
    ) -> AsyncIterator[Any]:
        raise NotImplementedError(f"{self.name} does not declare Capability.STREAMING")

    def supported_patterns(self) -> list[str]:
        """Pattern/topology vocabulary this adapter understands, for
        `validator.py`'s optional pattern-existence check. Adapters
        without a fixed pattern vocabulary (e.g. a loop-based adapter)
        return an empty list — validator treats that as "no constraint",
        not an error."""
        return []

    def export(self, compiled: CompiledArtifact) -> Any:
        """Export a compiled artifact back toward a portable form.

        Only meaningful if `Capability.ROUND_TRIP` is declared. Default
        raises — adapters that support round-tripping (e.g. a future
        Agent Spec bridge) override this.
        """
        raise NotImplementedError(f"{self.name} does not declare Capability.ROUND_TRIP")


class AdapterRegistry:
    """Discovers adapters via Python entry points.

    Core never imports any adapter package directly — third parties can
    ship a backend without touching this repo at all by registering an
    entry point in the ``pyagent_blueprint.adapters`` group.
    """

    GROUP = "pyagent_blueprint.adapters"

    @staticmethod
    def discover() -> dict[str, type[RuntimeAdapter]]:
        """Return all installed adapters, keyed by entry-point name.

        An entry point that fails to import (e.g. an adapter registered
        by `pyproject.toml` whose own optional dependency — like
        `pyagent-patterns` for the `pyagent` adapter — isn't installed)
        is skipped rather than raised: one adapter's missing dependency
        must never break discovery of every OTHER adapter. This is what
        lets `validate`/`generate` degrade gracefully with zero runtime
        packages installed, while the zero-dependency reference adapters
        remain fully discoverable.
        """
        import logging
        from importlib.metadata import entry_points

        logger = logging.getLogger(__name__)

        found: dict[str, type[RuntimeAdapter]] = {}
        try:
            eps = entry_points(group=AdapterRegistry.GROUP)
        except TypeError:  # pragma: no cover - py<3.10 signature fallback
            eps = entry_points().get(AdapterRegistry.GROUP, [])  # type: ignore[attr-defined]
        for ep in eps:
            try:
                found[ep.name] = ep.load()
            except ImportError as exc:
                logger.debug(
                    "Adapter '%s' could not be loaded (missing dependency?): %s", ep.name, exc
                )
                continue
        return found

    @staticmethod
    def get(name: str) -> type[RuntimeAdapter]:
        """Look up a single adapter class by entry-point name.

        Raises:
            KeyError: If no adapter is registered under `name`.
        """
        adapters = AdapterRegistry.discover()
        if name not in adapters:
            raise KeyError(
                f"No adapter registered as '{name}'. Installed: {sorted(adapters)}"
            )
        return adapters[name]
