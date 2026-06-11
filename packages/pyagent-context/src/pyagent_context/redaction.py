"""ContextRedactor: field-level redaction by sensitivity tier."""

from __future__ import annotations

from pyagent_context.item import SENSITIVITY_ORDER, ContextItem, Sensitivity
from pyagent_context.ledger import ContextLedger


class ContextRedactor:
    """Redact or filter context items based on sensitivity.

    Items above the allowed sensitivity threshold are either fully redacted
    (content replaced) or excluded entirely.

    Args:
        max_sensitivity: Maximum allowed sensitivity level. Items above
            this are redacted.
        redaction_text: Replacement text for redacted items.
        exclude_above: If ``True``, items above max_sensitivity are
            excluded instead of redacted.
    """

    def __init__(
        self,
        max_sensitivity: Sensitivity = Sensitivity.INTERNAL,
        redaction_text: str = "[REDACTED]",
        exclude_above: bool = False,
    ) -> None:
        self._max_sensitivity = max_sensitivity
        self._redaction_text = redaction_text
        self._exclude_above = exclude_above

    def redact_item(self, item: ContextItem) -> ContextItem | None:
        """Redact a single item if it exceeds the sensitivity threshold.

        Returns:
            The original item if within threshold, a redacted copy if above,
            or ``None`` if ``exclude_above`` is ``True`` and the item exceeds.
        """
        item_level = SENSITIVITY_ORDER.get(item.sensitivity, 0)
        max_level = SENSITIVITY_ORDER.get(self._max_sensitivity, 0)

        if item_level <= max_level:
            return item

        if self._exclude_above:
            return None

        return ContextItem(
            content=self._redaction_text,
            source=item.source,
            timestamp=item.timestamp,
            trust_level=item.trust_level,
            sensitivity=item.sensitivity,
            expires_at=item.expires_at,
            derived_from=item.id,
            token_estimate=max(1, len(self._redaction_text) // 4),
        )

    def redact_ledger(self, ledger: ContextLedger) -> ContextLedger:
        """Apply redaction to all items in a ledger.

        Returns:
            New ledger with redacted/filtered items.
        """
        new_items: list[ContextItem] = []
        for item in ledger.items:
            result = self.redact_item(item)
            if result is not None:
                new_items.append(result)
        return ContextLedger(items=new_items)
