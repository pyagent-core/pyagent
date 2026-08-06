"""Agent Unit packaging: turn a validated blueprint into a distributable artifact.

An "Agent Unit" is a self-describing archive containing:
  - the original blueprint spec (YAML)
  - a ``unit.json`` manifest (name, version, author, target runtime adapter,
    declared dependencies, and a content hash of the source spec)

This module is intentionally dependency-light: it only needs the blueprint
schema and, optionally, the adapter registry (to validate that ``runtime``
refers to something discoverable at packaging time — that check is skipped
gracefully if no adapters are installed at all, consistent with the rest of
the core package's zero-mandatory-dependency posture).
"""

from __future__ import annotations

import hashlib
import json
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pyagent_blueprint.schema.spec import BlueprintSpec


class PackagingError(Exception):
    """Raised when a blueprint cannot be packaged into an Agent Unit."""


@dataclass(frozen=True)
class AgentUnitMetadata:
    """Resolved, packaging-ready metadata for an Agent Unit."""

    name: str
    version: str
    author: str
    runtime: str
    dependencies: tuple[str, ...] = field(default_factory=tuple)
    spec_sha256: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "version": self.version,
            "author": self.author,
            "runtime": self.runtime,
            "dependencies": list(self.dependencies),
            "spec_sha256": self.spec_sha256,
            "unit_schema_version": "1.0",
        }


def _known_adapter_names() -> set[str] | None:
    """Return the set of discoverable adapter names, or None if the
    adapter registry itself cannot be imported (e.g. an extremely
    minimal install). Mirrors the graceful-degradation pattern used in
    validator.py / generator.py.
    """
    try:
        from pyagent_blueprint.adapter import AdapterRegistry
    except ImportError:
        return None

    try:
        return set(AdapterRegistry.discover())
    except Exception:
        return None


def build_metadata(spec: BlueprintSpec, raw_source: str) -> AgentUnitMetadata:
    """Validate and resolve packaging metadata from a loaded blueprint spec.

    Raises PackagingError if the spec has no ``package:`` block, or if its
    declared ``runtime`` does not match any discoverable adapter (only
    enforced when at least one adapter is discoverable at all — an
    environment with zero adapters installed cannot validate this and the
    check is skipped rather than failing).
    """
    if spec.package is None:
        raise PackagingError(
            "Blueprint has no 'package:' block. Add one with at least "
            "'name' and 'runtime' to package it as an Agent Unit."
        )

    pkg = spec.package
    known = _known_adapter_names()
    if known and pkg.runtime not in known:
        raise PackagingError(
            f"package.runtime={pkg.runtime!r} does not match any discoverable "
            f"adapter. Known adapters: {sorted(known)!r}. Install the adapter "
            "package that provides it, or fix the runtime name."
        )

    digest = hashlib.sha256(raw_source.encode("utf-8")).hexdigest()
    return AgentUnitMetadata(
        name=pkg.name,
        version=pkg.version,
        author=pkg.author,
        runtime=pkg.runtime,
        dependencies=tuple(pkg.dependencies),
        spec_sha256=digest,
    )


def package_blueprint(
    spec: BlueprintSpec,
    raw_source: str,
    source_filename: str,
    output_dir: str | Path,
) -> Path:
    """Build a distributable Agent Unit archive.

    Produces ``<output_dir>/<name>-<version>.agentunit.zip`` containing:
      - ``unit.json`` — the AgentUnitMetadata manifest
      - the original blueprint source, preserved under its own filename

    Returns the path to the written archive.
    """
    metadata = build_metadata(spec, raw_source)

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    archive_path = out_dir / f"{metadata.name}-{metadata.version}.agentunit.zip"

    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("unit.json", json.dumps(metadata.to_dict(), indent=2))
        zf.writestr(Path(source_filename).name, raw_source)

    return archive_path
