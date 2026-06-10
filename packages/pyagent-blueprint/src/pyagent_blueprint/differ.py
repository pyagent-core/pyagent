"""BlueprintDiffer: semantic diff between two BlueprintSpecs."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from pyagent_blueprint.schema.spec import BlueprintSpec


class ChangeType(StrEnum):
    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"


class ChangeSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    BREAKING = "breaking"


@dataclass(frozen=True)
class Change:
    """A single semantic change between two blueprint versions.

    Attributes:
        path: Dotted path to the changed field.
        change_type: Added, removed, or modified.
        old_value: Previous value (None for added).
        new_value: New value (None for removed).
        severity: Impact level.
    """

    path: str
    change_type: ChangeType
    old_value: Any
    new_value: Any
    severity: ChangeSeverity


# Fields whose modification is considered breaking
_BREAKING_FIELDS = {"pattern", "api_version"}
# Fields whose modification is a warning
_WARNING_FIELDS = {"prompt", "provider", "model", "recovery"}


class BlueprintDiffer:
    """Compute semantic diff between two blueprint specs."""

    def diff(self, old: BlueprintSpec, new: BlueprintSpec) -> list[Change]:
        """Diff two blueprint specs.

        Args:
            old: Previous version.
            new: Updated version.

        Returns:
            List of ``Change`` objects.
        """
        changes: list[Change] = []

        old_dict = old.model_dump()
        new_dict = new.model_dump()

        self._diff_dicts(old_dict, new_dict, "", changes)
        return changes

    def summary(self, changes: list[Change]) -> str:
        """Human-readable summary of changes.

        Args:
            changes: List from ``diff()``.

        Returns:
            Multi-line summary string.
        """
        if not changes:
            return "No changes detected."

        lines: list[str] = []
        for severity in (ChangeSeverity.BREAKING, ChangeSeverity.WARNING, ChangeSeverity.INFO):
            filtered = [c for c in changes if c.severity == severity]
            if filtered:
                lines.append(f"\n{severity.upper()} ({len(filtered)}):")
                for c in filtered:
                    lines.append(f"  [{c.change_type}] {c.path}")
        return "\n".join(lines)

    def _diff_dicts(
        self,
        old: dict,
        new: dict,
        prefix: str,
        changes: list[Change],
    ) -> None:
        """Recursively diff two dictionaries."""
        all_keys = set(old.keys()) | set(new.keys())

        for key in sorted(all_keys):
            path = f"{prefix}.{key}" if prefix else key
            old_val = old.get(key)
            new_val = new.get(key)

            if key not in old:
                changes.append(Change(
                    path=path,
                    change_type=ChangeType.ADDED,
                    old_value=None,
                    new_value=new_val,
                    severity=self._classify_severity(key, ChangeType.ADDED),
                ))
            elif key not in new:
                changes.append(Change(
                    path=path,
                    change_type=ChangeType.REMOVED,
                    old_value=old_val,
                    new_value=None,
                    severity=self._classify_severity(key, ChangeType.REMOVED),
                ))
            elif isinstance(old_val, dict) and isinstance(new_val, dict):
                self._diff_dicts(old_val, new_val, path, changes)
            elif old_val != new_val:
                changes.append(Change(
                    path=path,
                    change_type=ChangeType.MODIFIED,
                    old_value=old_val,
                    new_value=new_val,
                    severity=self._classify_severity(key, ChangeType.MODIFIED),
                ))

    @staticmethod
    def _classify_severity(field_name: str, change_type: ChangeType) -> ChangeSeverity:
        """Determine severity based on field name and change type."""
        if field_name in _BREAKING_FIELDS:
            return ChangeSeverity.BREAKING
        if change_type == ChangeType.REMOVED:
            return ChangeSeverity.WARNING
        if field_name in _WARNING_FIELDS:
            return ChangeSeverity.WARNING
        return ChangeSeverity.INFO
