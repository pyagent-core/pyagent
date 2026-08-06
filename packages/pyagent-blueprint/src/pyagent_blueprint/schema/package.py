"""PackageSpec: optional 'Agent Unit' packaging metadata for a blueprint.

This is a new, backward-compatible, optional top-level ``package:`` block.
Blueprints that omit it behave exactly as before. When present, it declares
enough information to build a distributable "Agent Unit": a name/version
for the unit itself, the runtime adapter it targets, and any extra
distribution dependencies.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class PackageSpec(BaseModel):
    """Optional packaging metadata for producing an 'Agent Unit' artifact."""

    name: str = Field(..., description="Distribution name for the packaged Agent Unit")
    version: str = Field(default="0.1.0", description="Semantic version of the Agent Unit")
    author: str = Field(default="", description="Author or team publishing this unit")
    runtime: str = Field(
        ...,
        description=(
            "Name of the RuntimeAdapter this unit targets (e.g. 'pyagent', "
            "'simple_loop', 'state_machine', 'sequential_chain', 'single_agent', "
            "or a third-party adapter name). Must match a discoverable adapter "
            "at packaging time."
        ),
    )
    dependencies: list[str] = Field(
        default_factory=list,
        description="Extra distribution dependencies beyond the runtime adapter itself",
    )
