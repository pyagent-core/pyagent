"""BlueprintSpec: root Pydantic model for a complete agent system specification."""

from __future__ import annotations

from pydantic import BaseModel, Field

from pyagent_blueprint.schema.agents import AgentSpec
from pyagent_blueprint.schema.context import ContextConfigSpec
from pyagent_blueprint.schema.contracts import ContractSpec
from pyagent_blueprint.schema.metadata import MetadataSpec
from pyagent_blueprint.schema.observability import ObservabilitySpec
from pyagent_blueprint.schema.providers import ProviderBindingSpec
from pyagent_blueprint.schema.workflows import WorkflowSpec


class BlueprintSpec(BaseModel):
    """Root specification for a declarative agent system.

    This is the top-level Pydantic model that represents a complete
    blueprint YAML/JSON document.
    """

    api_version: str = Field(default="pyagent/v1", description="Schema version")
    metadata: MetadataSpec
    providers: dict[str, ProviderBindingSpec] = Field(default_factory=dict)
    context: ContextConfigSpec | None = Field(default=None)
    agents: dict[str, AgentSpec]
    workflows: dict[str, WorkflowSpec]
    contracts: dict[str, ContractSpec] = Field(default_factory=dict)
    observability: ObservabilitySpec | None = Field(default=None)
