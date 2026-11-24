"""Grants, the authority graph, downward delegation, and call-time authorization.

This is the authorization plane. A record (see ``records.py``) says what something is. Nothing
in this module treats a discovered or verified record as permission: a call is allowed only
when a live grant covers this principal, action, capability, purpose, and data.
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

from pyagent_dns.records import (
    SENSITIVITY_ORDER,
    VALID_DATA_CLASSES,
    RecordStatus,
    check_keys,
    ensure_aware,
    parse_expiry,
)
from pyagent_dns.signing import VerificationStatus

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Mapping, Sequence

    from pyagent_dns.registry import NameRegistry
    from pyagent_dns.resolver import Resolution

# Reason codes are public API: adding one is additive, renaming one is a breaking change.
GRANT_FOUND = "GRANT_FOUND"
NO_RECORD = "NO_RECORD"
NO_GRANT = "NO_GRANT"
GRANT_EXPIRED = "GRANT_EXPIRED"
RECORD_UNVERIFIED = "RECORD_UNVERIFIED"
RECORD_SIGNATURE_INVALID = "RECORD_SIGNATURE_INVALID"
RECORD_REVOKED = "RECORD_REVOKED"
RECORD_EXPIRED = "RECORD_EXPIRED"
RECORD_DEPRECATED = "RECORD_DEPRECATED"
PURPOSE_MISMATCH = "PURPOSE_MISMATCH"
DATA_CLASS_EXCEEDED = "DATA_CLASS_EXCEEDED"
LIMIT_EXCEEDED = "LIMIT_EXCEEDED"
SESSION_LIMIT_EXCEEDED = "SESSION_LIMIT_EXCEEDED"
AMOUNT_LIMIT_EXCEEDED = "AMOUNT_LIMIT_EXCEEDED"
DELEGATION_NOT_ALLOWED = "DELEGATION_NOT_ALLOWED"
"""Reserved. ``authorize`` cannot produce it in 0.1, because ``add_grant`` refuses a child of a
grant that does not allow delegation. ``delegate`` reports that case as ``AttenuationError``
with dimension ``delegation.allowed``."""
CHAIN_BROKEN = "CHAIN_BROKEN"
APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
APPROVAL_DENIED = "APPROVAL_DENIED"
OBLIGATION_UNAVAILABLE = "OBLIGATION_UNAVAILABLE"


class GrantLoadError(ValueError):
    """Raised when a grant is malformed, whether loaded from a file or built in code."""


class Action(StrEnum):
    """What a principal may do with a capability."""

    READ = "read"
    WRITE = "write"
    CALL = "call"
    DELEGATE = "delegate"
    APPROVE = "approve"
    EXPORT = "export"
    EXECUTE = "execute"
    SPEND = "spend"
    DELETE = "delete"


HIGH_RISK_ACTIONS: frozenset[Action] = frozenset(
    {Action.WRITE, Action.EXPORT, Action.SPEND, Action.DELETE}
)


class GrantEffect(StrEnum):
    """What a matching grant does: allow outright, or hold the call for approval."""

    ALLOW = "allow"
    REQUIRE_APPROVAL = "require_approval"


class Outcome(StrEnum):
    """The four structured results of an authorization check."""

    ALLOW = "allow"
    ALLOW_WITH_OBLIGATIONS = "allow_with_obligations"
    REQUIRE_APPROVAL = "require_approval"
    DENY = "deny"


class Obligation(StrEnum):
    """Something the caller must do for an allow to be honored. One that cannot be done is a deny."""

    LOG_DECISION = "log_decision"
    REDACT = "redact"
    REQUIRE_APPROVAL_BOUND_TO_HASH = "require_approval_bound_to_hash"
    COUNT_AGAINST_BUDGET = "count_against_budget"


def _rank(data_classes: Iterable[str]) -> int:
    """Highest sensitivity rank among ``data_classes``; 0 (public) if there are none."""
    return max((SENSITIVITY_ORDER[d] for d in data_classes), default=0)


def _inherit(requested: Any, inherited: Any) -> Any:
    """``requested`` unless it is ``None``, in which case the parent's value is inherited."""
    return inherited if requested is None else requested


def _optional_str(data: Mapping[str, Any], key: str, where: str) -> str | None:
    value = data.get(key)
    if value is not None and not isinstance(value, str):
        raise GrantLoadError(f"{where}: '{key}' must be a string, got {value!r}")
    return value


@dataclass(frozen=True)
class Limits:
    """Numeric ceilings. ``None`` means this link does not bound that dimension.

    Args:
        max_records_per_call: Most records one call may request.
        max_calls_per_session: Most calls allowed within one session.
        max_amount: Largest amount one call may spend. A grant that sets this must set
            ``currency``, since an amount with no currency cannot be compared.
        currency: Currency ``max_amount`` is in.
    """

    max_records_per_call: int | None = None
    max_calls_per_session: int | None = None
    max_amount: float | None = None
    currency: str | None = None

    def __post_init__(self) -> None:
        for name in ("max_records_per_call", "max_calls_per_session"):
            value = getattr(self, name)
            if value is not None and (
                isinstance(value, bool) or not isinstance(value, int) or value < 0
            ):
                raise GrantLoadError(f"{name} must be a non-negative integer, got {value!r}")
        amount = self.max_amount
        if amount is not None and (
            isinstance(amount, bool) or not isinstance(amount, (int, float)) or amount < 0
        ):
            raise GrantLoadError(f"max_amount must be a non-negative number, got {amount!r}")

    def to_dict(self) -> dict[str, Any]:
        """Return the limits as a plain dictionary."""
        return {
            "max_records_per_call": self.max_records_per_call,
            "max_calls_per_session": self.max_calls_per_session,
            "max_amount": self.max_amount,
            "currency": self.currency,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any], *, where: str = "limits") -> Limits:
        """Build from a mapping, rejecting unknown keys."""
        check_keys(
            data,
            required=[],
            optional=["max_records_per_call", "max_calls_per_session", "max_amount", "currency"],
            where=where,
            error=GrantLoadError,
        )
        try:
            return cls(**dict(data))
        except GrantLoadError as exc:
            raise GrantLoadError(f"{where}: {exc}") from None


@dataclass(frozen=True)
class ResourceSelector:
    """The data a call touches, or the data a grant covers.

    Args:
        data_classes: Sensitivity classes. A grant covers a request when its highest class
            is at least the request's highest class, so a grant for ``internal`` covers
            ``public`` and ``internal`` but not ``confidential``. A grant naming none covers
            only public data.
        account_scope: Account the call is for. A grant that sets it requires an exact match.
        name_scope: Exact record name; there are no glob patterns in 0.1.
    """

    data_classes: tuple[str, ...] = ()
    account_scope: str | None = None
    name_scope: str | None = None

    def __post_init__(self) -> None:
        if isinstance(self.data_classes, str):
            raise GrantLoadError(
                f"data_classes must be a sequence of strings, got {self.data_classes!r}"
            )
        object.__setattr__(self, "data_classes", tuple(self.data_classes))
        for data_class in self.data_classes:
            if data_class not in VALID_DATA_CLASSES:
                raise GrantLoadError(
                    f"Unknown data class '{data_class}'. Expected one of: {sorted(VALID_DATA_CLASSES)}"
                )

    def to_dict(self) -> dict[str, Any]:
        """Return the selector as a plain dictionary."""
        return {
            "data_classes": list(self.data_classes),
            "account_scope": self.account_scope,
            "name_scope": self.name_scope,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any], *, where: str = "resource") -> ResourceSelector:
        """Build from a mapping, rejecting unknown keys."""
        check_keys(
            data,
            required=[],
            optional=["data_classes", "account_scope", "name_scope"],
            where=where,
            error=GrantLoadError,
        )
        data_classes = data.get("data_classes", [])
        if not isinstance(data_classes, list):
            raise GrantLoadError(f"{where}: 'data_classes' must be a list, got {data_classes!r}")
        try:
            return cls(
                data_classes=tuple(data_classes),
                account_scope=_optional_str(data, "account_scope", where),
                name_scope=_optional_str(data, "name_scope", where),
            )
        except GrantLoadError as exc:
            raise GrantLoadError(f"{where}: {exc}") from None


@dataclass(frozen=True)
class DelegationTerms:
    """Whether a grant may be delegated.

    ``must_attenuate`` means a delegate must hold strictly less authority than the grant
    on at least one dimension. When False, a delegate may hold an equal grant. In neither
    case may a delegate hold more: attenuation is a ceiling.
    """

    allowed: bool = False
    must_attenuate: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Return the terms as a plain dictionary."""
        return {"allowed": self.allowed, "must_attenuate": self.must_attenuate}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any], *, where: str = "delegation") -> DelegationTerms:
        """Build from a mapping. Values must be real booleans.

        ``bool("false")`` is True, so a quoted YAML value is rejected rather than coerced.
        """
        check_keys(
            data,
            required=[],
            optional=["allowed", "must_attenuate"],
            where=where,
            error=GrantLoadError,
        )
        for key, value in data.items():
            if not isinstance(value, bool):
                raise GrantLoadError(f"{where}: '{key}' must be true or false, got {value!r}")
        return cls(**dict(data))


@dataclass(frozen=True)
class Grant:
    """Permission for one principal to perform one action on one capability.

    Args:
        grant_id: Stable identifier. Decision logs and delegation chains refer to it.
        principal: Who holds the grant.
        action: What it permits.
        capability: What it applies to: a record name, or one of a record's capabilities.
        resource: Data the grant covers.
        purpose: Why the grant exists. A call for a different purpose is not covered.
        limits: Numeric ceilings.
        delegation: Whether and how the grant may be delegated.
        effect: ``ALLOW``, or ``REQUIRE_APPROVAL`` to hold each call for a human.
        approver_role: Who should approve, for ``REQUIRE_APPROVAL``. Informational.
        granted_by: Policy that issued it.
        policy_version: Version of that policy, so a log can name the deciding policy.
        expires: Timezone-aware expiry, or ``None``.
        parent_grant_id: The grant this was delegated from, if any.
    """

    grant_id: str
    principal: str
    action: Action
    capability: str
    resource: ResourceSelector = ResourceSelector()
    purpose: str = ""
    limits: Limits = Limits()
    delegation: DelegationTerms = DelegationTerms()
    effect: GrantEffect = GrantEffect.ALLOW
    approver_role: str | None = None
    granted_by: str = ""
    policy_version: str = ""
    expires: datetime | None = None
    parent_grant_id: str | None = None

    def __post_init__(self) -> None:
        for name in ("grant_id", "principal", "capability"):
            if not getattr(self, name):
                raise GrantLoadError(f"grant {name} must not be empty")
        if self.expires is not None:
            ensure_aware(self.expires, f"grant '{self.grant_id}' expires")
        if self.limits.max_amount is not None and not self.limits.currency:
            raise GrantLoadError(f"grant '{self.grant_id}': max_amount requires a currency")

    def is_expired(self, now: datetime | None = None) -> bool:
        """Return whether the grant's expiry has passed at ``now`` (default: current UTC time)."""
        if self.expires is None:
            return False
        current = datetime.now(UTC) if now is None else ensure_aware(now, "now")
        return current > self.expires

    def to_dict(self) -> dict[str, Any]:
        """Return the grant as a plain dictionary that :meth:`from_dict` accepts."""
        return {
            "grant_id": self.grant_id,
            "principal": self.principal,
            "action": str(self.action),
            "capability": self.capability,
            "resource": self.resource.to_dict(),
            "purpose": self.purpose,
            "limits": self.limits.to_dict(),
            "delegation": self.delegation.to_dict(),
            "effect": str(self.effect),
            "approver_role": self.approver_role,
            "granted_by": self.granted_by,
            "policy_version": self.policy_version,
            "expires": self.expires.astimezone(UTC).isoformat() if self.expires else None,
            "parent_grant_id": self.parent_grant_id,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any], *, where: str = "grant") -> Grant:
        """Build a grant from a mapping.

        ``grant_id``, ``principal``, ``action``, ``capability``, and ``purpose`` are required,
        and unknown keys are rejected. A misspelled ``effect`` must not fall back to
        ``allow``, and an id generated at load time would differ on every run and could not
        be referenced by a delegation or a decision log.

        A single ``granted_by: policy_v14`` is accepted and split into ``granted_by`` and
        ``policy_version`` when ``policy_version`` is absent.

        Raises:
            GrantLoadError: On a missing, unknown, or malformed field.
        """
        required = ["grant_id", "principal", "action", "capability", "purpose"]
        optional = ["resource", "limits", "delegation", "effect", "approver_role", "granted_by"]
        optional += ["policy_version", "expires", "parent_grant_id"]
        check_keys(data, required=required, optional=optional, where=where, error=GrantLoadError)
        for key in ("grant_id", "principal", "capability", "purpose"):
            if not isinstance(data[key], str):
                raise GrantLoadError(f"{where}: '{key}' must be a string, got {data[key]!r}")
        for key in ("resource", "limits", "delegation"):
            if key in data and not isinstance(data[key], dict):
                raise GrantLoadError(f"{where}: '{key}' must be a mapping")
        try:
            action = Action(data["action"])
            effect = GrantEffect(data.get("effect", "allow"))
        except ValueError as exc:
            raise GrantLoadError(f"{where}: {exc}") from None

        granted_by = _optional_str(data, "granted_by", where) or ""
        policy_version = _optional_str(data, "policy_version", where) or ""
        if granted_by and not policy_version and "_v" in granted_by:
            granted_by, version = granted_by.rsplit("_v", 1)
            policy_version = f"v{version}"

        try:
            return cls(
                grant_id=data["grant_id"],
                principal=data["principal"],
                action=action,
                capability=data["capability"],
                resource=ResourceSelector.from_dict(
                    data.get("resource", {}), where=f"{where}.resource"
                ),
                purpose=data["purpose"],
                limits=Limits.from_dict(data.get("limits", {}), where=f"{where}.limits"),
                delegation=DelegationTerms.from_dict(
                    data.get("delegation", {}), where=f"{where}.delegation"
                ),
                effect=effect,
                approver_role=_optional_str(data, "approver_role", where),
                granted_by=granted_by,
                policy_version=policy_version,
                expires=parse_expiry(
                    data.get("expires"), where=f"{where}.expires", error=GrantLoadError
                ),
                parent_grant_id=_optional_str(data, "parent_grant_id", where),
            )
        except GrantLoadError as exc:
            raise GrantLoadError(f"{where}: {exc}") from None


def load_grants_file(path: str | Path) -> list[Grant]:
    """Load grants from a YAML or JSON file holding a list, or a ``grants:`` list.

    Raises:
        FileNotFoundError: If the file does not exist.
        GrantLoadError: If the file is unparseable or any grant is invalid. Messages name the
            file and the grant's position.
    """
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"Grants file not found: {file_path}")
    try:
        data = yaml.safe_load(file_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise GrantLoadError(f"{file_path}: cannot parse: {exc}") from exc
    if data is None:
        return []
    if isinstance(data, dict) and set(data) == {"grants"}:
        data = data["grants"]
    if not isinstance(data, list):
        raise GrantLoadError(f"{file_path}: expected a list of grants")
    grants: list[Grant] = []
    for index, item in enumerate(data):
        where = f"{file_path}: grant[{index}]"
        if not isinstance(item, dict):
            raise GrantLoadError(f"{where}: expected a mapping, got {type(item).__name__}")
        grants.append(Grant.from_dict(item, where=where))
    return grants


@dataclass(frozen=True)
class CallContext:
    """Facts about one call, supplied by the caller.

    ``calls_in_session``, ``records_requested``, and ``amount`` are taken on trust: a caller
    that always passes zero has disabled that limit. ``DnsMiddleware`` keeps a real session
    counter; a direct caller of ``authorize`` must supply one.

    Args:
        purpose: Why this call is being made.
        session_id: Identifies the session, for logging.
        calls_in_session: Calls already made this session.
        records_requested: Records this call asks for, if known.
        amount: Amount this call would spend, if any.
        currency: Currency of ``amount``.
        request_payload: Exact request bytes. An approval is bound to their SHA-256 and the
            bytes themselves are never stored.
    """

    purpose: str
    session_id: str | None = None
    calls_in_session: int = 0
    records_requested: int | None = None
    amount: float | None = None
    currency: str | None = None
    request_payload: bytes | None = None


@dataclass(frozen=True)
class Decision:
    """The result of an authorization check, with the evidence needed to explain it later.

    Args:
        outcome: ``ALLOW``, ``ALLOW_WITH_OBLIGATIONS``, ``REQUIRE_APPROVAL``, or ``DENY``.
        reason_code: Stable code naming the check that decided it.
        reason: Human-readable explanation.
        principal: The leaf principal the check was for.
        action: Action requested.
        capability: Capability requested.
        grant_path: Grant ids root first, leaf last, that authorized the call.
        effective_limits: Limits intersected along that path.
        obligations: What must be done for an allow to be honored.
        approval_binding: ``sha256:`` of the request an approval must be bound to.
        data_classes: Data classes the check evaluated: what the caller declared plus what
            the resolved record declares.
        record_name: Record the call resolved to.
        record_fingerprint: Digest of the exact record bytes resolved.
        record_version: Version resolved.
        record_verification: Signature verification outcome for that record.
        policy_versions: Versions of the policies that issued the grants on the path.
    """

    outcome: Outcome
    reason_code: str
    reason: str
    principal: str
    action: Action
    capability: str
    grant_path: tuple[str, ...] = ()
    effective_limits: Limits | None = None
    obligations: tuple[Obligation, ...] = ()
    approval_binding: str | None = None
    data_classes: tuple[str, ...] = ()
    record_name: str | None = None
    record_fingerprint: str | None = None
    record_version: str | None = None
    record_verification: VerificationStatus | None = None
    policy_versions: tuple[str, ...] = ()

    @property
    def allowed(self) -> bool:
        """True for ``ALLOW`` and ``ALLOW_WITH_OBLIGATIONS`` only."""
        return self.outcome in (Outcome.ALLOW, Outcome.ALLOW_WITH_OBLIGATIONS)

    def to_dict(self) -> dict[str, Any]:
        """Return the decision as a plain dictionary."""
        return {
            "outcome": str(self.outcome),
            "reason_code": self.reason_code,
            "reason": self.reason,
            "principal": self.principal,
            "action": str(self.action),
            "capability": self.capability,
            "grant_path": list(self.grant_path),
            "effective_limits": self.effective_limits.to_dict() if self.effective_limits else None,
            "obligations": [str(o) for o in self.obligations],
            "approval_binding": self.approval_binding,
            "data_classes": list(self.data_classes),
            "record_name": self.record_name,
            "record_fingerprint": self.record_fingerprint,
            "record_version": self.record_version,
            "record_verification": str(self.record_verification)
            if self.record_verification
            else None,
            "policy_versions": list(self.policy_versions),
        }


@dataclass(frozen=True)
class GrantScope:
    """The scope requested for a delegate. ``None`` means inherit the parent's value."""

    resource: ResourceSelector | None = None
    purpose: str | None = None
    limits: Limits | None = None
    expires: datetime | None = None


@dataclass(frozen=True)
class DelegationToken:
    """A structured record of a delegation chain.

    It is data, not a signed credential: the issuer and the checker are the same process in
    0.1, so the graph can re-derive and re-check the chain. A portable signed format is a
    later decision.
    """

    token_id: str
    grant_chain: tuple[str, ...]
    principal_chain: tuple[str, ...]
    effective_limits: Limits
    expires: datetime | None
    token_hash: str


@dataclass(frozen=True)
class DelegationResult:
    """A delegated grant, and the token describing its chain."""

    grant: Grant
    token: DelegationToken


class AttenuationError(Exception):
    """Raised when a delegate would hold more authority than its parent.

    Attributes:
        dimension: The field that would widen, for example ``limits.max_amount``.
        parent_value: The parent's value.
        requested_value: The requested value.
    """

    def __init__(
        self, dimension: str, parent_value: Any, requested_value: Any, message: str | None = None
    ) -> None:
        super().__init__(
            message
            or f"Delegation would exceed its parent on {dimension}: "
            f"parent={parent_value!r}, requested={requested_value!r}"
        )
        self.dimension = dimension
        self.parent_value = parent_value
        self.requested_value = requested_value


_Failure = tuple[str, str]


class AuthorityGraph:
    """Grants and the delegation links between them, plus call-time authorization.

    Not thread-safe; see ``NameRegistry``.

    Args:
        registry: Registry the graph reports coverage against. ``uncovered`` and
            ``revoke_record`` need one.
        clock: Epoch-seconds time source. Defaults to the registry's, else wall-clock time.
    """

    def __init__(
        self, registry: NameRegistry | None = None, *, clock: Callable[[], float] | None = None
    ) -> None:
        self._registry = registry
        self._clock = clock or (registry.clock if registry else time.time)
        self._grants: dict[str, Grant] = {}
        self._revoked: set[str] = set()

    @property
    def registry(self) -> NameRegistry | None:
        """The bound registry, if any."""
        return self._registry

    def _now(self) -> datetime:
        return datetime.fromtimestamp(self._clock(), UTC)

    def _live(self, grant: Grant) -> bool:
        return grant.grant_id not in self._revoked and not grant.is_expired(self._now())

    # -- Grants ---------------------------------------------------------------------------

    def add_grant(self, grant: Grant) -> str:
        """Add a grant and return its id.

        A grant that names a parent is checked against it: the parent must exist and allow
        delegation, and the grant must not exceed it on any dimension. The graph therefore
        holds no grant broader than its parent, however the grant was authored.

        Raises:
            ValueError: If the id is already used, or the parent is missing.
            AttenuationError: If the grant exceeds its parent.
        """
        if grant.grant_id in self._grants:
            raise ValueError(f"Grant id '{grant.grant_id}' is already in the graph")
        if grant.parent_grant_id is not None:
            parent = self._grants.get(grant.parent_grant_id)
            if parent is None:
                raise ValueError(
                    f"Grant '{grant.grant_id}' names parent '{grant.parent_grant_id}', which is not in the graph"
                )
            self._assert_attenuates(parent, grant)
        self._grants[grant.grant_id] = grant
        return grant.grant_id

    def add_grants(self, grants: Iterable[Grant]) -> None:
        """Add several grants, parents before children whatever their order in the input.

        All or nothing: if any grant is rejected, none of them are added.
        """
        pending = list(grants)
        added: list[str] = []
        try:
            while pending:
                ready = [
                    g
                    for g in pending
                    if g.parent_grant_id is None or g.parent_grant_id in self._grants
                ]
                if not ready:
                    missing = sorted({g.parent_grant_id or "" for g in pending})
                    raise ValueError(
                        f"Grants name parent(s) not in the graph: {', '.join(missing)}"
                    )
                for grant in ready:
                    added.append(self.add_grant(grant))
                    pending.remove(grant)
        except Exception:
            for grant_id in added:
                del self._grants[grant_id]
            raise

    def get_grant(self, grant_id: str) -> Grant | None:
        """Return a grant, or ``None`` if it is unknown or revoked."""
        return None if grant_id in self._revoked else self._grants.get(grant_id)

    def grants_for(self, principal: str, action: Action | None = None) -> list[Grant]:
        """Return a principal's unrevoked, unexpired grants. Ancestry is not checked."""
        return [
            g
            for g in self._grants.values()
            if g.principal == principal and (action is None or g.action == action) and self._live(g)
        ]

    def revoke(self, grant_id: str) -> bool:
        """Revoke a grant. Returns True if it was present and not already revoked.

        Grants delegated from it stop authorizing on the next check, because every check
        validates the whole chain.
        """
        if grant_id in self._grants and grant_id not in self._revoked:
            self._revoked.add(grant_id)
            return True
        return False

    def is_revoked(self, grant_id: str) -> bool:
        """Return whether a grant has been revoked."""
        return grant_id in self._revoked

    def revoke_record(self, name: str, version: str | None = None) -> bool:
        """Revoke a record in the bound registry, so both halves of an incident response
        can be done from one handle."""
        if self._registry is None:
            raise ValueError("No registry is bound to this AuthorityGraph")
        return self._registry.revoke(name, version)

    # -- Delegation -----------------------------------------------------------------------

    def delegate(
        self, parent_grant_id: str, *, delegate_principal: str, scope: GrantScope
    ) -> DelegationResult:
        """Issue a grant to ``delegate_principal`` that is no broader than its parent.

        Fields left ``None`` in ``scope`` are inherited. Capability, action, and effect are
        always inherited: a delegate that needs a different capability needs its own grant
        from a policy owner, and delegation can never weaken an approval requirement.

        Raises:
            ValueError: If the parent is unknown, revoked, or expired.
            AttenuationError: If the parent does not allow delegation, the scope exceeds
                the parent on any dimension, or the parent requires attenuation and the
                scope narrows nothing. ``dimension`` names the offending field.
        """
        parent = self._grants.get(parent_grant_id)
        if parent is None:
            raise ValueError(f"Parent grant '{parent_grant_id}' not found")
        if not self._live(parent):
            raise ValueError(f"Parent grant '{parent_grant_id}' is revoked or expired")

        resource, limits = scope.resource or ResourceSelector(), scope.limits or Limits()
        child = Grant(
            grant_id=uuid.uuid4().hex,
            principal=delegate_principal,
            action=parent.action,
            capability=parent.capability,
            resource=ResourceSelector(
                data_classes=resource.data_classes or parent.resource.data_classes,
                account_scope=_inherit(resource.account_scope, parent.resource.account_scope),
                name_scope=_inherit(resource.name_scope, parent.resource.name_scope),
            ),
            purpose=_inherit(scope.purpose, parent.purpose),
            limits=Limits(
                max_records_per_call=_inherit(
                    limits.max_records_per_call, parent.limits.max_records_per_call
                ),
                max_calls_per_session=_inherit(
                    limits.max_calls_per_session, parent.limits.max_calls_per_session
                ),
                max_amount=_inherit(limits.max_amount, parent.limits.max_amount),
                currency=limits.currency or parent.limits.currency,
            ),
            delegation=parent.delegation,
            effect=parent.effect,
            approver_role=parent.approver_role,
            granted_by=parent.granted_by,
            policy_version=parent.policy_version,
            expires=_inherit(scope.expires, parent.expires),
            parent_grant_id=parent.grant_id,
        )
        self.add_grant(child)

        chain, _ = self._chain(child)
        token_id = uuid.uuid4().hex
        effective = self._limits_along(chain)
        canonical = json.dumps(
            {
                "token_id": token_id,
                "grant_chain": [g.grant_id for g in chain],
                "principal_chain": [g.principal for g in chain],
                "effective_limits": effective.to_dict(),
                "expires": child.expires.isoformat() if child.expires else None,
            },
            sort_keys=True,
        ).encode()
        token = DelegationToken(
            token_id=token_id,
            grant_chain=tuple(g.grant_id for g in chain),
            principal_chain=tuple(g.principal for g in chain),
            effective_limits=effective,
            expires=child.expires,
            token_hash=f"sha256:{hashlib.sha256(canonical).hexdigest()}",
        )
        return DelegationResult(grant=child, token=token)

    @staticmethod
    def _assert_attenuates(parent: Grant, child: Grant) -> None:
        """Raise ``AttenuationError`` unless ``child`` is within ``parent`` on every dimension."""
        if not parent.delegation.allowed:
            raise AttenuationError("delegation.allowed", False, True)
        for dimension in ("action", "capability"):
            if getattr(child, dimension) != getattr(parent, dimension):
                raise AttenuationError(
                    dimension, getattr(parent, dimension), getattr(child, dimension)
                )
        if child.purpose != parent.purpose:
            raise AttenuationError("purpose", parent.purpose, child.purpose)
        if parent.effect == GrantEffect.REQUIRE_APPROVAL and child.effect != parent.effect:
            raise AttenuationError("effect", parent.effect, child.effect)

        p_res, c_res = parent.resource, child.resource
        if _rank(c_res.data_classes) > _rank(p_res.data_classes):
            raise AttenuationError("resource.data_classes", p_res.data_classes, c_res.data_classes)
        for scope in ("account_scope", "name_scope"):
            p_val, c_val = getattr(p_res, scope), getattr(c_res, scope)
            if p_val is not None and c_val != p_val:
                raise AttenuationError(f"resource.{scope}", p_val, c_val)

        p_lim, c_lim = parent.limits, child.limits
        for name in ("max_records_per_call", "max_calls_per_session", "max_amount"):
            p_val, c_val = getattr(p_lim, name), getattr(c_lim, name)
            if p_val is not None and (c_val is None or c_val > p_val):
                raise AttenuationError(f"limits.{name}", p_val, c_val)
        if p_lim.currency is not None and c_lim.currency != p_lim.currency:
            raise AttenuationError("limits.currency", p_lim.currency, c_lim.currency)

        if parent.expires is not None and (child.expires is None or child.expires > parent.expires):
            raise AttenuationError("expires", parent.expires, child.expires)

        if parent.delegation.must_attenuate and not _narrows(parent, child):
            raise AttenuationError(
                "must_attenuate",
                "full scope",
                "full scope",
                message=(
                    "The parent grant requires attenuation: a delegate must narrow at least one "
                    "of data classes, scope, limits, or expiry"
                ),
            )

    # -- Chains and limits ----------------------------------------------------------------

    def _chain(self, grant: Grant) -> tuple[list[Grant], _Failure | None]:
        """Walk ``grant`` up to its root. Returns the chain root first, and why it is broken."""
        chain, seen, current = [grant], {grant.grant_id}, grant
        while current.parent_grant_id is not None:
            parent = self._grants.get(current.parent_grant_id)
            if parent is None or parent.grant_id in seen or not self._live(parent):
                return chain, (
                    CHAIN_BROKEN,
                    f"Grant '{current.grant_id}' derives from '{current.parent_grant_id}', "
                    "which is missing, revoked, or expired",
                )
            chain.insert(0, parent)
            seen.add(parent.grant_id)
            current = parent
        return chain, None

    @staticmethod
    def _limits_along(chain: Sequence[Grant]) -> Limits:
        """Intersect limits along a chain: the minimum of each bounded dimension."""

        def tightest(values: list[Any]) -> Any:
            bounded = [v for v in values if v is not None]
            return min(bounded) if bounded else None

        return Limits(
            max_records_per_call=tightest([g.limits.max_records_per_call for g in chain]),
            max_calls_per_session=tightest([g.limits.max_calls_per_session for g in chain]),
            max_amount=tightest([g.limits.max_amount for g in chain]),
            currency=next((g.limits.currency for g in reversed(chain) if g.limits.currency), None),
        )

    def _select(
        self,
        principal_chain: Sequence[str],
        action: Action,
        capability: str,
        *,
        purpose: str | None,
        data_classes: tuple[str, ...],
        account_scope: str | None,
        name_scope: str | None,
    ) -> tuple[list[Grant] | None, _Failure | None]:
        """Pick the grant that authorizes a call, or say why none does.

        The one place grant selection happens, so ``authorize`` and ``effective_limit``
        cannot disagree about which grant, and therefore which limits, apply. The check order
        is: a grant exists, purpose, data coverage, expiry, then chain integrity. The first
        failing check is the one reported.
        """
        leaf = principal_chain[-1]
        candidates = [
            g
            for g in self._grants.values()
            if g.principal == leaf
            and g.action == action
            and g.capability == capability
            and g.grant_id not in self._revoked
        ]
        if not candidates:
            return None, (
                NO_GRANT,
                f"No covering grant for principal '{leaf}', action '{action}', capability '{capability}'",
            )

        if purpose is not None:
            matching = [g for g in candidates if g.purpose == purpose]
            if not matching:
                held = sorted({g.purpose for g in candidates})
                return None, (PURPOSE_MISMATCH, f"Call purpose is '{purpose}'; grants cover {held}")
            candidates = matching

        covering: list[Grant] = []
        gap = ""
        for grant in candidates:
            problem = self._coverage_gap(grant, data_classes, account_scope, name_scope)
            if problem is None:
                covering.append(grant)
            else:
                gap = gap or problem
        if not covering:
            return None, (DATA_CLASS_EXCEEDED, gap)

        now = self._now()
        live = [g for g in covering if not g.is_expired(now)]
        if not live:
            return None, (
                GRANT_EXPIRED,
                f"Grant '{covering[0].grant_id}' expired at {covering[0].expires}",
            )

        failure: _Failure | None = None
        for grant in live:
            chain, broken = self._chain(grant)
            if broken is None and len(principal_chain) > 1:
                actual = [g.principal for g in chain]
                if actual != list(principal_chain):
                    broken = (
                        CHAIN_BROKEN,
                        f"Principal chain {list(principal_chain)} does not match the grant's "
                        f"delegation chain {actual}",
                    )
            if broken is None:
                return chain, None
            failure = failure or broken
        return None, failure

    @staticmethod
    def _coverage_gap(
        grant: Grant,
        data_classes: tuple[str, ...],
        account_scope: str | None,
        name_scope: str | None,
    ) -> str | None:
        """Return why ``grant`` does not cover the request, or ``None`` if it does."""
        held = _rank(grant.resource.data_classes)
        if _rank(data_classes) > held:
            exceeded = next(d for d in data_classes if SENSITIVITY_ORDER[d] > held)
            return f"Requested data class '{exceeded}' exceeds what grant '{grant.grant_id}' covers"
        for label, wanted, offered in (
            ("account", grant.resource.account_scope, account_scope),
            ("name", grant.resource.name_scope, name_scope),
        ):
            if wanted is not None and wanted != offered:
                return f"Grant '{grant.grant_id}' is scoped to {label} '{wanted}', not '{offered}'"
        return None

    # -- Queries --------------------------------------------------------------------------

    def effective_limit(
        self,
        principal_chain: Sequence[str],
        action: Action,
        capability: str,
        resource: ResourceSelector,
        *,
        purpose: str | None = None,
    ) -> Limits | None:
        """Return the limits that would bind this call, or ``None`` if no grant authorizes it.

        Uses the same grant selection as :meth:`authorize`. Pass ``purpose`` when grants for
        the same capability differ by purpose, since their limits may differ.
        """
        if not principal_chain:
            return None
        chain, _ = self._select(
            principal_chain,
            action,
            capability,
            purpose=purpose,
            data_classes=resource.data_classes,
            account_scope=resource.account_scope,
            name_scope=resource.name_scope,
        )
        return None if chain is None else self._limits_along(chain)

    def reachable(self, principal: str, purpose: str | None = None) -> list[str]:
        """Return the sorted capabilities a principal can currently reach.

        A grant counts only if it is live and its whole delegation chain is intact.
        """
        return sorted(
            {
                g.capability
                for g in self.grants_for(principal)
                if (purpose is None or g.purpose == purpose) and self._chain(g)[1] is None
            }
        )

    def uncovered(self) -> list[str]:
        """Return the sorted names of usable records that no live grant covers.

        A grant covers a record when its capability is the record's name or one of the
        record's capabilities, and its name scope, if set, is that record's name.

        Raises:
            ValueError: If no registry is bound. Returning ``[]`` there would claim nothing
                is uncovered when nothing was checked.
        """
        if self._registry is None:
            raise ValueError("Cannot report uncovered records without a bound registry")
        grants = [g for g in self._grants.values() if self._live(g) and self._chain(g)[1] is None]
        return sorted(
            record.name
            for record in self._registry.discover(verified_only=False)
            if not any(
                g.capability in (record.name, *record.capabilities)
                and g.resource.name_scope in (None, record.name)
                for g in grants
            )
        )

    # -- Authorization --------------------------------------------------------------------

    def authorize(
        self,
        principal_chain: Sequence[str],
        action: Action,
        capability: str,
        resource: ResourceSelector,
        context: CallContext,
        resolution: Resolution | None = None,
    ) -> Decision:
        """Decide whether ``principal_chain`` may perform ``action`` on ``capability``.

        Checks run in a fixed order and the first failure is named in the decision's reason
        code: the resolved record (revoked, expired, signature, verification), then a covering
        grant (existence, purpose, data coverage, expiry, delegation chain), then limits, then
        the grant's effect. A discovered or verified record is never enough on its own.

        When a ``resolution`` is given, its record is authoritative about what is being
        touched. The record's data classes are a floor under whatever the caller declares, so
        a caller cannot understate sensitivity, and the record's name is the name scope.
        ``capability`` must be the record's name or one of its declared capabilities.

        Pure given the graph, the registry state, and the injected clock: no I/O.
        """
        if not principal_chain:
            return Decision(
                outcome=Outcome.DENY,
                reason_code=NO_GRANT,
                reason="Empty principal chain",
                principal="",
                action=action,
                capability=capability,
            )
        leaf = principal_chain[-1]
        record = resolution.record if resolution else None
        data_classes, name_scope, note = resource.data_classes, resource.name_scope, ""

        def decide(outcome: Outcome, code: str, reason: str, **extra: Any) -> Decision:
            return Decision(
                outcome=outcome,
                reason_code=code,
                reason=reason,
                principal=leaf,
                action=action,
                capability=capability,
                data_classes=data_classes,
                record_name=record.name if record else None,
                record_fingerprint=resolution.fingerprint if resolution else None,
                record_version=resolution.version if resolution else None,
                record_verification=resolution.verification if resolution else None,
                **extra,
            )

        def deny(code: str, reason: str, **extra: Any) -> Decision:
            return decide(Outcome.DENY, code, reason, **extra)

        # 1. The resolved record.
        if resolution is not None and record is not None:
            if capability != record.name and capability not in record.capabilities:
                return deny(NO_RECORD, f"Record '{record.name}' does not declare '{capability}'")
            if resolution.status == RecordStatus.REVOKED:
                return deny(RECORD_REVOKED, f"Record '{record.name}' has been revoked")
            if record.is_expired(self._now()):
                return deny(RECORD_EXPIRED, f"Record '{record.name}' expired at {record.expires}")
            if resolution.verification == VerificationStatus.FAILED:
                return deny(
                    RECORD_SIGNATURE_INVALID,
                    f"Signature verification failed for record '{record.name}'",
                )
            data_classes = tuple(dict.fromkeys((*resource.data_classes, *record.data_classes)))
            name_scope = record.name
            if resolution.verification == VerificationStatus.UNVERIFIED:
                public_read = (
                    action == Action.READ and bool(data_classes) and set(data_classes) == {"public"}
                )
                if not public_read:
                    return deny(
                        RECORD_UNVERIFIED,
                        f"Record '{record.name}' is unverified; only reads of public data are allowed",
                    )
            if resolution.status == RecordStatus.DEPRECATED:
                note = f" (record '{record.name}' is deprecated: {RECORD_DEPRECATED})"

        # 2-6. A covering grant, with an intact delegation chain.
        chain, failure = self._select(
            principal_chain,
            action,
            capability,
            purpose=context.purpose,
            data_classes=data_classes,
            account_scope=resource.account_scope,
            name_scope=name_scope,
        )
        if chain is None or failure is not None:
            code, reason = failure or (NO_GRANT, "No covering grant")
            return deny(code, reason)
        grant = chain[-1]
        path = tuple(g.grant_id for g in chain)
        versions = tuple(dict.fromkeys(g.policy_version for g in chain if g.policy_version))
        limits = self._limits_along(chain)
        evidence: dict[str, Any] = {
            "grant_path": path,
            "effective_limits": limits,
            "policy_versions": versions,
        }

        # 7. Limits.
        if (
            limits.max_records_per_call is not None
            and context.records_requested is not None
            and context.records_requested > limits.max_records_per_call
        ):
            return deny(
                LIMIT_EXCEEDED,
                f"records_requested ({context.records_requested}) exceeds limit "
                f"({limits.max_records_per_call})",
                **evidence,
            )
        if (
            limits.max_calls_per_session is not None
            and context.calls_in_session >= limits.max_calls_per_session
        ):
            return deny(
                SESSION_LIMIT_EXCEEDED,
                f"{context.calls_in_session} calls already made this session; "
                f"the limit is {limits.max_calls_per_session}",
                **evidence,
            )
        if limits.max_amount is not None:
            if context.amount is None and action == Action.SPEND:
                return deny(
                    AMOUNT_LIMIT_EXCEEDED,
                    "A spend under an amount limit must state its amount",
                    **evidence,
                )
            if context.amount is not None:
                if context.currency != limits.currency:
                    return deny(
                        AMOUNT_LIMIT_EXCEEDED,
                        f"Currency mismatch: limit is in '{limits.currency}', call is in '{context.currency}'",
                        **evidence,
                    )
                if context.amount > limits.max_amount:
                    return deny(
                        AMOUNT_LIMIT_EXCEEDED,
                        f"amount ({context.amount}) exceeds limit ({limits.max_amount})",
                        **evidence,
                    )

        # 8. The grant's effect.
        if grant.effect == GrantEffect.REQUIRE_APPROVAL:
            if context.request_payload is None:
                return deny(
                    APPROVAL_REQUIRED,
                    "An approval cannot be bound to an unhashed request: request_payload is missing",
                    **evidence,
                )
            digest = hashlib.sha256(context.request_payload).hexdigest()
            return decide(
                Outcome.REQUIRE_APPROVAL,
                GRANT_FOUND,
                f"Approval required for '{capability}' by role '{grant.approver_role}'{note}",
                obligations=(Obligation.REQUIRE_APPROVAL_BOUND_TO_HASH, Obligation.LOG_DECISION),
                approval_binding=f"sha256:{digest}",
                **evidence,
            )

        obligations: list[Obligation] = []
        # A tool call returning confidential data is a read, so CALL is treated like READ here.
        if _rank(data_classes) >= SENSITIVITY_ORDER["confidential"] and action in (
            Action.READ,
            Action.EXPORT,
            Action.CALL,
        ):
            obligations.append(Obligation.REDACT)
        if limits.max_calls_per_session is not None or limits.max_amount is not None:
            obligations.append(Obligation.COUNT_AGAINST_BUDGET)
        if obligations or action in HIGH_RISK_ACTIONS or len(chain) > 1:
            obligations.insert(0, Obligation.LOG_DECISION)

        return decide(
            Outcome.ALLOW_WITH_OBLIGATIONS if obligations else Outcome.ALLOW,
            GRANT_FOUND,
            f"Authorized under grant '{grant.grant_id}'{note}",
            obligations=tuple(obligations),
            **evidence,
        )


def _narrows(parent: Grant, child: Grant) -> bool:
    """Whether ``child`` is strictly narrower than ``parent`` on at least one dimension."""
    p_res, c_res = parent.resource, child.resource
    p_lim, c_lim = parent.limits, child.limits
    return (
        _rank(c_res.data_classes) < _rank(p_res.data_classes)
        or (p_res.account_scope is None and c_res.account_scope is not None)
        or (p_res.name_scope is None and c_res.name_scope is not None)
        or any(
            getattr(c_lim, n) is not None
            and (getattr(p_lim, n) is None or getattr(c_lim, n) < getattr(p_lim, n))
            for n in ("max_records_per_call", "max_calls_per_session", "max_amount")
        )
        or (
            child.expires is not None and (parent.expires is None or child.expires < parent.expires)
        )
        or (parent.effect == GrantEffect.ALLOW and child.effect == GrantEffect.REQUIRE_APPROVAL)
    )
