"""Custom OTel attributes for pyagent spans.

All attributes are namespaced under `pyagent.*` to avoid collisions.
Follows OpenTelemetry GenAI semantic conventions where applicable.
"""

from __future__ import annotations


class PyAgentAttributes:
    """Attribute key constants for pyagent OTel spans."""

    # Pattern attributes
    PATTERN_TYPE = "pyagent.pattern.type"
    PATTERN_ROUNDS = "pyagent.pattern.rounds"
    PATTERN_CONSENSUS = "pyagent.pattern.consensus"
    PATTERN_ESCALATED = "pyagent.pattern.escalated"
    PATTERN_ESCALATION_LEVEL = "pyagent.pattern.escalation_level"

    # Router attributes
    ROUTER_DIFFICULTY = "pyagent.router.difficulty"
    ROUTER_DIFFICULTY_CATEGORY = "pyagent.router.difficulty_category"
    ROUTER_SELECTED_MODEL = "pyagent.router.selected_model"
    ROUTER_COST_ESTIMATE = "pyagent.router.cost_estimate"
    ROUTER_ALTERNATIVES = "pyagent.router.alternatives"

    # Compression attributes
    COMPRESS_INPUT_TOKENS = "pyagent.compress.input_tokens"
    COMPRESS_OUTPUT_TOKENS = "pyagent.compress.output_tokens"
    COMPRESS_SAVINGS_PCT = "pyagent.compress.savings_pct"

    # Agent attributes
    AGENT_NAME = "pyagent.agent.name"
    AGENT_ROLE = "pyagent.agent.role"
    AGENT_CONTRIBUTION = "pyagent.agent.contribution"

    # Cost attributes
    COST_TOTAL_USD = "pyagent.cost.total_usd"
    COST_INPUT_TOKENS = "pyagent.cost.input_tokens"
    COST_OUTPUT_TOKENS = "pyagent.cost.output_tokens"
    COST_MODEL = "pyagent.cost.model"

    # Execution attributes
    EXEC_DURATION_MS = "pyagent.exec.duration_ms"
    EXEC_TOKEN_ESTIMATE = "pyagent.exec.token_estimate"
    EXEC_LLM_CALLS = "pyagent.exec.llm_calls"
