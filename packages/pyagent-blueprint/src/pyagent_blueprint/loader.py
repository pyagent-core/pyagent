"""Loader: load and validate blueprint YAML/JSON files into BlueprintSpec."""

from __future__ import annotations

import json
from pathlib import Path

import yaml
from pydantic import ValidationError

from pyagent_blueprint.schema.spec import BlueprintSpec


class BlueprintLoadError(Exception):
    """Raised when a blueprint cannot be loaded or validated."""


def load_blueprint(path: str | Path) -> BlueprintSpec:
    """Load a blueprint from a YAML or JSON file.

    Args:
        path: Path to a ``.yaml``, ``.yml``, or ``.json`` file.

    Returns:
        Validated ``BlueprintSpec``.

    Raises:
        BlueprintLoadError: If the file is missing, unreadable, or invalid.
    """
    path = Path(path)

    if not path.exists():
        raise BlueprintLoadError(f"Blueprint file not found: {path}")

    text = path.read_text(encoding="utf-8")

    try:
        if path.suffix in (".yaml", ".yml"):
            data = yaml.safe_load(text)
        elif path.suffix == ".json":
            data = json.loads(text)
        else:
            raise BlueprintLoadError(f"Unsupported file extension: {path.suffix}")
    except (yaml.YAMLError, json.JSONDecodeError) as exc:
        raise BlueprintLoadError(f"Parse error in {path}: {exc}") from exc

    if not isinstance(data, dict):
        raise BlueprintLoadError(f"Blueprint must be a mapping, got {type(data).__name__}")

    try:
        return BlueprintSpec(**data)
    except ValidationError as exc:
        raise BlueprintLoadError(f"Schema validation failed for {path}:\n{exc}") from exc


def load_blueprint_from_str(text: str, fmt: str = "yaml") -> BlueprintSpec:
    """Load a blueprint from a string.

    Args:
        text: YAML or JSON text.
        fmt: ``"yaml"`` or ``"json"``.

    Returns:
        Validated ``BlueprintSpec``.
    """
    if fmt == "json":
        data = json.loads(text)
    else:
        data = yaml.safe_load(text)

    return BlueprintSpec(**data)
