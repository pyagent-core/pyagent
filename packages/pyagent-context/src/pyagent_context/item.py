"""ContextItem: content + metadata with trust, sensitivity, and lifecycle."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import StrEnum


class TrustLevel(StrEnum):
    """Trust classification for context items."""

    VERIFIED = "verified"  # from trusted source, validated
    INFERRED = "inferred"  # LLM-generated, not validated
    USER_PROVIDED = "user"  # direct user input
    EXTERNAL = "external"  # from tool/API call

    def __ge__(self, other: TrustLevel) -> bool:
        order = {
            TrustLevel.INFERRED: 0,
            TrustLevel.EXTERNAL: 1,
            TrustLevel.USER_PROVIDED: 2,
            TrustLevel.VERIFIED: 3,
        }
        return order.get(self, 0) >= order.get(other, 0)

    def __gt__(self, other: TrustLevel) -> bool:
        return self != other and self.__ge__(other)

    def __le__(self, other: TrustLevel) -> bool:
        return other.__ge__(self)

    def __lt__(self, other: TrustLevel) -> bool:
        return self != other and self.__le__(other)


# Numeric ordering for scoring
TRUST_ORDER: dict[TrustLevel, int] = {
    TrustLevel.INFERRED: 0,
    TrustLevel.EXTERNAL: 1,
    TrustLevel.USER_PROVIDED: 2,
    TrustLevel.VERIFIED: 3,
}


class Sensitivity(StrEnum):
    """Data sensitivity classification."""

    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


SENSITIVITY_ORDER: dict[Sensitivity, int] = {
    Sensitivity.PUBLIC: 0,
    Sensitivity.INTERNAL: 1,
    Sensitivity.CONFIDENTIAL: 2,
    Sensitivity.RESTRICTED: 3,
}


@dataclass
class ContextItem:
    """A single piece of context with trust and lifecycle metadata.

    Attributes:
        content: The text content.
        source: Origin — agent name, tool name, or ``"user"``.
        timestamp: Creation time (``time.time()``).
        trust_level: How much to trust this item.
        sensitivity: Data classification for redaction decisions.
        expires_at: Expiration timestamp, or ``None`` for never.
        derived_from: Parent item ID if this was derived from another.
        token_estimate: Rough token count (``len(content) // 4``).
    """

    content: str
    source: str
    timestamp: float = field(default_factory=time.time)
    trust_level: TrustLevel = TrustLevel.INFERRED
    sensitivity: Sensitivity = Sensitivity.INTERNAL
    expires_at: float | None = None
    derived_from: str | None = None
    token_estimate: int = 0
    _id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])

    def __post_init__(self) -> None:
        if self.token_estimate == 0:
            self.token_estimate = max(1, len(self.content) // 4)

    @property
    def id(self) -> str:
        return self._id

    @property
    def is_expired(self) -> bool:
        """Check if this item has passed its expiry time."""
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at

    @property
    def age_seconds(self) -> float:
        """Time since creation in seconds."""
        return time.time() - self.timestamp

    def to_dict(self) -> dict:
        """Serialize to a JSON-compatible dict."""
        return {
            "id": self._id,
            "content": self.content,
            "source": self.source,
            "timestamp": self.timestamp,
            "trust_level": self.trust_level.value,
            "sensitivity": self.sensitivity.value,
            "expires_at": self.expires_at,
            "derived_from": self.derived_from,
            "token_estimate": self.token_estimate,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ContextItem:
        """Deserialize from a dict."""
        item = cls(
            content=data["content"],
            source=data["source"],
            timestamp=data["timestamp"],
            trust_level=TrustLevel(data["trust_level"]),
            sensitivity=Sensitivity(data["sensitivity"]),
            expires_at=data.get("expires_at"),
            derived_from=data.get("derived_from"),
            token_estimate=data.get("token_estimate", 0),
        )
        item._id = data["id"]
        return item
