"""Stable diagnostic-code registry.

Maps the ten Agent-Spec gaps (G1-G10) identified in the transformation plan
to stable, machine-checkable diagnostic codes. Adapters return these (via
`CompileDiagnostic`) instead of silently dropping a governance feature they
can't honor. `info`-severity codes (e.g. `PATTERN_LOWERED`) are expected and
not failures; `warning`/`error` codes indicate a governance feature was
requested by the blueprint but not enforced by the target adapter.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class DiagnosticSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True)
class DiagnosticCode:
    code: str
    severity: DiagnosticSeverity
    gap: str
    description: str


# G1 — no provider registry / routing semantics
ROUTING_UNSUPPORTED = DiagnosticCode(
    code="ROUTING_UNSUPPORTED",
    severity=DiagnosticSeverity.WARNING,
    gap="G1",
    description="Blueprint declares provider fallback/routing that this adapter cannot enforce.",
)

# G2 — no declarative cost/token/latency budgets or SLAs
BUDGET_UNSUPPORTED = DiagnosticCode(
    code="BUDGET_UNSUPPORTED",
    severity=DiagnosticSeverity.WARNING,
    gap="G2",
    description="Blueprint declares a cost/token budget that this adapter cannot enforce.",
)
SLA_UNSUPPORTED = DiagnosticCode(
    code="SLA_UNSUPPORTED",
    severity=DiagnosticSeverity.WARNING,
    gap="G2",
    description="Blueprint declares an SLA (latency/cost/quality) that this adapter cannot enforce.",
)

# G3 — no memory-tier model (trust, sensitivity, expiry, redaction)
MEMORY_TIER_UNSUPPORTED = DiagnosticCode(
    code="MEMORY_TIER_UNSUPPORTED",
    severity=DiagnosticSeverity.WARNING,
    gap="G3",
    description="Blueprint declares a memory/context policy that this adapter cannot enforce.",
)

# G4 — thin named-pattern vocabulary; hand-wired flows lose design intent
PATTERN_LOWERED = DiagnosticCode(
    code="PATTERN_LOWERED",
    severity=DiagnosticSeverity.INFO,
    gap="G4",
    description="Named pattern was lowered to a generic graph/loop; intent preserved via annotation.",
)

# G6 — HITL is tool-confirmation only, no workflow-level checkpoint
CHECKPOINT_UNSUPPORTED = DiagnosticCode(
    code="CHECKPOINT_UNSUPPORTED",
    severity=DiagnosticSeverity.WARNING,
    gap="G6",
    description="Blueprint declares a human-in-the-loop checkpoint that this adapter cannot enforce.",
)

# G7 — guardrails not first-class
GUARDRAIL_UNSUPPORTED = DiagnosticCode(
    code="GUARDRAIL_UNSUPPORTED",
    severity=DiagnosticSeverity.WARNING,
    gap="G7",
    description="Blueprint declares guardrails that this adapter cannot enforce.",
)

# G8 — recovery only partially declarative
RECOVERY_UNSUPPORTED = DiagnosticCode(
    code="RECOVERY_UNSUPPORTED",
    severity=DiagnosticSeverity.WARNING,
    gap="G8",
    description="Blueprint declares a retry/backoff/fallback recovery policy that this adapter cannot enforce.",
)

# G9 — no round-trip conformance profile
LOSSY_ROUNDTRIP = DiagnosticCode(
    code="LOSSY_ROUNDTRIP",
    severity=DiagnosticSeverity.WARNING,
    gap="G9",
    description="Exporting/importing this construct does not round-trip losslessly on this adapter.",
)

ALL_CODES: tuple[DiagnosticCode, ...] = (
    ROUTING_UNSUPPORTED,
    BUDGET_UNSUPPORTED,
    SLA_UNSUPPORTED,
    MEMORY_TIER_UNSUPPORTED,
    PATTERN_LOWERED,
    CHECKPOINT_UNSUPPORTED,
    GUARDRAIL_UNSUPPORTED,
    RECOVERY_UNSUPPORTED,
    LOSSY_ROUNDTRIP,
)

CODES_BY_NAME: dict[str, DiagnosticCode] = {c.code: c for c in ALL_CODES}


def code_for(name: str) -> DiagnosticCode:
    """Look up a diagnostic code by its stable string name.

    Raises:
        KeyError: If `name` isn't a registered diagnostic code.
    """
    return CODES_BY_NAME[name]
