"""Load an ``x-pyagent:dns`` block from a blueprint file.

Round-trip limitation, stated here so no one has to discover it: the block survives on disk,
because nothing in 0.1 rewrites the blueprint file, but it does **not** survive
pyagent-blueprint's own load, compile, diff, or render path. ``BlueprintSpec`` silently drops
unknown top-level keys and the IR is built from the spec. That is why this module reads the
raw YAML itself, and why tooling built on pyagent-blueprint cannot see the dns configuration:
changing a grants file reference produces no blueprint diff. Fixing that means choosing an
``extra`` keys policy for ``BlueprintSpec``, a decision for the blueprint maintainers and not
something this package should force.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from pyagent_dns.authority import AttenuationError, AuthorityGraph, load_grants_file
from pyagent_dns.diagnostics import AUTHORITY_UNSUPPORTED, DNS_UNSUPPORTED
from pyagent_dns.records import load_records_file
from pyagent_dns.registry import NameRegistry
from pyagent_dns.resolver import Resolver
from pyagent_dns.signing import TrustedKeys

if TYPE_CHECKING:
    from collections.abc import Mapping

EXTENSION_KEY = "x-pyagent:dns"
"""Equal to ``pyagent_blueprint.extensions.namespaced_key("dns")``; a test keeps them in step."""


class DnsBlueprintError(ValueError):
    """A blueprint's dns block is malformed, or names a file that cannot be used."""


class DnsEnforcement(StrEnum):
    """How strictly a blueprint's dns configuration must load.

    ``REQUIRED``: any problem raises, because silently ignoring a malformed security block is
    the worst available outcome. ``ADVISORY``: a problem is reported as a warning and no
    bundle is returned, for blueprints that must still load without it.
    """

    REQUIRED = "required"
    ADVISORY = "advisory"


class DnsExtensionSpec(BaseModel):
    """The shape of the ``x-pyagent:dns`` block. Unknown keys are rejected."""

    model_config = ConfigDict(extra="forbid")

    records_files: list[str] = Field(default_factory=list)
    grants_files: list[str] = Field(default_factory=list)
    trusted_keys_file: str | None = None
    enforcement: DnsEnforcement = DnsEnforcement.REQUIRED


@dataclass
class DnsBundle:
    """A blueprint's dns configuration, loaded and wired together."""

    spec: DnsExtensionSpec
    registry: NameRegistry
    resolver: Resolver
    graph: AuthorityGraph
    source_path: Path | None = None


def load_dns_block(raw_blueprint: Mapping[str, Any]) -> DnsExtensionSpec | None:
    """Parse the dns block from a raw blueprint mapping.

    Returns ``None`` only when the key is absent, which is the common case and costs nothing.
    A key that is present but empty or not a mapping is an error.

    Raises:
        DnsBlueprintError: If the block is not a mapping, or has an unknown or invalid key.
    """
    key = EXTENSION_KEY
    if key not in raw_blueprint:
        return None
    block = raw_blueprint[key]
    if not isinstance(block, dict):
        raise DnsBlueprintError(f"'{key}' must be a mapping, got {type(block).__name__}")
    try:
        return DnsExtensionSpec.model_validate(block)
    except ValidationError as exc:
        raise DnsBlueprintError(f"'{key}' is invalid: {exc}") from exc


def _existing(base_dir: Path, name: str, label: str) -> Path:
    path = base_dir / name
    if not path.is_file():
        raise DnsBlueprintError(f"{label} '{name}' not found at {path}")
    return path


def _build_bundle(spec: DnsExtensionSpec, blueprint_path: Path) -> DnsBundle:
    base_dir = blueprint_path.parent
    trusted_keys = None
    if spec.trusted_keys_file:
        trusted_keys = TrustedKeys.from_file(
            _existing(base_dir, spec.trusted_keys_file, "trusted_keys_file")
        )
    registry = NameRegistry(trusted_keys=trusted_keys)
    for index, name in enumerate(spec.records_files):
        registry.register_many(
            load_records_file(_existing(base_dir, name, f"records_files[{index}]"))
        )
    graph = AuthorityGraph(registry)
    for index, name in enumerate(spec.grants_files):
        graph.add_grants(load_grants_file(_existing(base_dir, name, f"grants_files[{index}]")))
    return DnsBundle(
        spec=spec,
        registry=registry,
        resolver=Resolver(registry),
        graph=graph,
        source_path=blueprint_path,
    )


def load_blueprint_dns(path: str | Path) -> DnsBundle | None:
    """Load a blueprint's ``x-pyagent:dns`` block into a wired :class:`DnsBundle`.

    Relative file references resolve against the blueprint's directory, not the working
    directory. Returns ``None`` if the blueprint has no dns block.

    Raises:
        FileNotFoundError: If the blueprint file does not exist.
        DnsBlueprintError: If the block, or any file it references, is invalid. The message
            names the blueprint. With ``enforcement: advisory`` this becomes a warning and
            ``None`` is returned instead.
    """
    blueprint_path = Path(path)
    if not blueprint_path.exists():
        raise FileNotFoundError(f"Blueprint file not found: {blueprint_path}")
    try:
        data = yaml.safe_load(blueprint_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise DnsBlueprintError(f"{blueprint_path}: cannot parse: {exc}") from exc
    if not isinstance(data, dict):
        raise DnsBlueprintError(f"{blueprint_path}: a blueprint must be a mapping")

    try:
        spec = load_dns_block(data)
    except DnsBlueprintError as exc:
        raise DnsBlueprintError(f"{blueprint_path}: {exc}") from None
    if spec is None:
        return None

    try:
        return _build_bundle(spec, blueprint_path)
    except (OSError, ValueError, AttenuationError) as exc:
        message = f"{blueprint_path}: {EXTENSION_KEY}: {exc}"
        if spec.enforcement == DnsEnforcement.ADVISORY:
            warnings.warn(
                f"{message} (enforcement is advisory; no dns bundle was loaded)", stacklevel=2
            )
            return None
        raise DnsBlueprintError(message) from exc


def adapter_diagnostics(bundle_present: bool, *, adapter_capabilities: set[str]) -> list[str]:
    """Return the diagnostic codes for a dns block that an adapter cannot honor.

    No adapter declares ``dns`` support in 0.1, so any blueprint with a dns block compiled
    onto one yields both codes. Wiring this into each adapter's compile path is a separate,
    later change in pyagent-blueprint.
    """
    if not bundle_present or "dns" in adapter_capabilities:
        return []
    return [DNS_UNSUPPORTED, AUTHORITY_UNSUPPORTED]
