"""Extension namespace + schema-version immutability policy.

Addresses OASF-gap items 3 and 4 from TRANSFORMATION-PLAN.md Section 1a,
and gives the future Agent Spec bridge (Step 8) a reserved place to put
constructs Agent Spec has no native concept for (routing, budgets,
memory tiers, guardrails, recovery, HITL checkpoints) without forking
the core schema.
"""

from __future__ import annotations

from dataclasses import dataclass

#: Reserved key prefix for third-party / non-core extensions, mirroring
#: the pattern used by Agent Spec's own Component `metadata` field and by
#: OASF's `modules` extension mechanism. Any key under this namespace is
#: additive and MUST be ignored gracefully by consumers that don't
#: recognize it (round-trip-safe by construction).
EXTENSION_NAMESPACE = "x-pyagent"


@dataclass(frozen=True)
class SchemaVersionPolicy:
    """Immutability policy for a published `api_version`.

    Mirrors OASF's schema versioning discipline: once a version ships, no
    breaking changes to it — only non-breaking doc/bugfix corrections.
    Any structural addition/removal bumps the version.
    """

    version: str
    frozen: bool
    notes: str = ""


#: Registry of shipped schema versions and their immutability status.
#: `pyagent/v1` is frozen (existing, load-only) — see
#: TRANSFORMATION-PLAN.md Section 1a gap #4 and the mega plan's "v1
#: blueprints keep working" design principle.
SCHEMA_VERSIONS: dict[str, SchemaVersionPolicy] = {
    "pyagent/v1": SchemaVersionPolicy(
        version="pyagent/v1",
        frozen=True,
        notes="Original schema. Loadable indefinitely; no breaking changes permitted.",
    ),
}


def is_frozen(api_version: str) -> bool:
    """Return whether `api_version` is a frozen (immutable) schema version.

    Unknown versions are treated as NOT frozen (still in development).
    """
    policy = SCHEMA_VERSIONS.get(api_version)
    return policy.frozen if policy else False


def namespaced_key(key: str) -> str:
    """Build a reserved extension key, e.g. ``namespaced_key("routing")``
    -> ``"x-pyagent:routing"``."""
    return f"{EXTENSION_NAMESPACE}:{key}"
