"""BlueprintService: load, validate, compile blueprints for the studio."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from pyagent_blueprint import (
    BlueprintCompiler,
    BlueprintValidator,
    RuntimeGraph,
    load_blueprint,
)

if TYPE_CHECKING:
    from pyagent_blueprint.schema import BlueprintSpec
    from pyagent_blueprint.validator import ValidationIssue


class BlueprintService:
    """Headless service for loading, validating, and compiling blueprints.

    Wraps ``pyagent-blueprint`` for use by TUI screens and tests.
    """

    def __init__(self) -> None:
        self._compiler = BlueprintCompiler()
        self._validator = BlueprintValidator()
        self._spec: BlueprintSpec | None = None
        self._graph: RuntimeGraph | None = None
        self._path: Path | None = None

    def load(self, path: str | Path) -> BlueprintSpec:
        """Load a blueprint from file.

        Args:
            path: Path to YAML/JSON blueprint.

        Returns:
            Validated ``BlueprintSpec``.

        Raises:
            BlueprintLoadError: On load/validation failure.
        """
        self._path = Path(path)
        self._spec = load_blueprint(self._path)
        self._graph = None
        return self._spec

    def validate(self) -> list[ValidationIssue]:
        """Run static validation on the loaded spec.

        Returns:
            List of validation issues.

        Raises:
            RuntimeError: If no spec loaded.
        """
        if self._spec is None:
            raise RuntimeError("No blueprint loaded. Call load() first.")
        return self._validator.validate(self._spec)

    def compile(self) -> RuntimeGraph:
        """Compile the loaded spec into a RuntimeGraph.

        Returns:
            Executable ``RuntimeGraph``.

        Raises:
            RuntimeError: If no spec loaded.
        """
        if self._spec is None:
            raise RuntimeError("No blueprint loaded. Call load() first.")
        self._graph = self._compiler.compile(self._spec)
        return self._graph

    def discover_blueprints(self, directory: str | Path = ".") -> list[Path]:
        """Find all YAML/JSON blueprint files in a directory.

        Args:
            directory: Root directory to search.

        Returns:
            List of file paths.
        """
        root = Path(directory)
        files: list[Path] = []
        for ext in ("*.yaml", "*.yml", "*.json"):
            files.extend(root.glob(f"**/{ext}"))
        return sorted(files)

    @property
    def spec(self) -> BlueprintSpec | None:
        return self._spec

    @property
    def graph(self) -> RuntimeGraph | None:
        return self._graph

    @property
    def path(self) -> Path | None:
        return self._path

    def summary(self) -> dict[str, Any]:
        """Quick summary of loaded blueprint."""
        if self._spec is None:
            return {"loaded": False}
        return {
            "loaded": True,
            "name": self._spec.metadata.name,
            "version": self._spec.metadata.version,
            "agents": len(self._spec.agents),
            "workflows": len(self._spec.workflows),
            "providers": len(self._spec.providers),
            "contracts": len(self._spec.contracts),
        }
