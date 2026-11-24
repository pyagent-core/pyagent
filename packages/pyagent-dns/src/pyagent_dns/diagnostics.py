"""Diagnostic codes for a blueprint whose dns block the target adapter cannot honor.

Both codes are NEW: neither exists in pyagent-blueprint today. They are defined here, in the
same shape pyagent-blueprint uses, so this package need not import it. ``gap`` carries
``G11 (proposed)`` because blueprint's gap ids G1 to G10 come from its transformation plan and
naming plus authorization maps onto none of them; the id is for the blueprint maintainer to
assign when the codes are registered there.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

DNS_UNSUPPORTED = "DNS_UNSUPPORTED"
AUTHORITY_UNSUPPORTED = "AUTHORITY_UNSUPPORTED"


@dataclass(frozen=True)
class DiagnosticCode:
    """A stable diagnostic code. Mirrors ``pyagent_blueprint.diagnostics.DiagnosticCode``.

    ``severity`` uses the same lowercase values: ``info``, ``warning``, ``error``.
    """

    code: str
    severity: str
    gap: str
    description: str


ALL_CODES: tuple[DiagnosticCode, ...] = (
    DiagnosticCode(
        code=DNS_UNSUPPORTED,
        severity="warning",
        gap="G11 (proposed)",
        description="Blueprint declares an x-pyagent:dns block that this adapter cannot resolve or verify.",
    ),
    DiagnosticCode(
        code=AUTHORITY_UNSUPPORTED,
        severity="warning",
        gap="G11 (proposed)",
        description="Blueprint declares grants in an x-pyagent:dns block that this adapter cannot enforce.",
    ),
)

CODES_BY_NAME: dict[str, DiagnosticCode] = {c.code: c for c in ALL_CODES}


def code_for(code: str) -> DiagnosticCode:
    """Return the ``DiagnosticCode`` named ``code``.

    Raises:
        KeyError: If the code is not defined here.
    """
    try:
        return CODES_BY_NAME[code]
    except KeyError:
        raise KeyError(f"Unknown diagnostic code: {code}") from None


def to_compile_diagnostic(code: DiagnosticCode | str, path: str, detail: str = "") -> Any:
    """Build a real ``pyagent_blueprint`` ``CompileDiagnostic`` for use inside a compile flow.

    Args:
        code: A code, or its name.
        path: Dotted path into the blueprint that triggered it, for example ``x-pyagent:dns``.
        detail: Adapter-specific detail. Defaults to the code's description.

    Raises:
        ImportError: If pyagent-blueprint is not installed.
    """
    try:
        from pyagent_blueprint.adapter import CompileDiagnostic
        from pyagent_blueprint.diagnostics import DiagnosticCode as BlueprintCode
        from pyagent_blueprint.diagnostics import DiagnosticSeverity
    except ImportError as exc:
        raise ImportError(
            "pyagent-blueprint is required to build a CompileDiagnostic. "
            "Install 'pyagent-dns[blueprint]'."
        ) from exc

    local = code_for(code) if isinstance(code, str) else code
    real = BlueprintCode(
        code=local.code,
        severity=DiagnosticSeverity(local.severity),
        gap=local.gap,
        description=local.description,
    )
    return CompileDiagnostic(code=real, path=path, detail=detail or local.description)
