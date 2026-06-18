"""Hardcoded sample dashboard data shown when no trace file is loaded."""

from __future__ import annotations

from typing import Any

_DELTA_LABEL = "vs previous hour"

KPIS: dict[str, dict[str, Any]] = {
    "total_runs": {
        "label": "Total Runs",
        "value": "1,248",
        "delta_pct": 18.7,
        "delta_label": _DELTA_LABEL,
        "direction": "up",
    },
    "success_rate": {
        "label": "Success Rate",
        "value": "96.3%",
        "delta_pct": 2.4,
        "delta_label": _DELTA_LABEL,
        "direction": "up",
    },
    "total_cost": {
        "label": "Total Cost",
        "value": "$124.58",
        "delta_pct": -8.2,
        "delta_label": _DELTA_LABEL,
        "direction": "down",
    },
    "total_tokens": {
        "label": "Total Tokens",
        "value": "2.45M",
        "delta_pct": -12.6,
        "delta_label": _DELTA_LABEL,
        "direction": "down",
    },
    "avg_latency": {
        "label": "Avg Latency",
        "value": "1.42s",
        "delta_pct": -15.3,
        "delta_label": _DELTA_LABEL,
        "direction": "down",
    },
}

RECENT_RUNS: list[dict[str, Any]] = [
    {
        "run_id": "run_01H7Z8K9",
        "workflow": "customer-support",
        "status": "success",
        "duration_s": 18.4,
        "cost_usd": 0.23,
        "started_at": "10:00:12 AM",
    },
    {
        "run_id": "run_01H7Z8K8",
        "workflow": "customer-support",
        "status": "success",
        "duration_s": 22.1,
        "cost_usd": 0.31,
        "started_at": "09:59:48 AM",
    },
    {
        "run_id": "run_01H7Z8K7",
        "workflow": "refund-processor",
        "status": "success",
        "duration_s": 31.7,
        "cost_usd": 0.42,
        "started_at": "09:59:31 AM",
    },
    {
        "run_id": "run_01H7Z8K6",
        "workflow": "data-analyst",
        "status": "failed",
        "duration_s": 12.8,
        "cost_usd": 0.07,
        "started_at": "09:59:10 AM",
    },
    {
        "run_id": "run_01H7Z8K5",
        "workflow": "customer-support",
        "status": "success",
        "duration_s": 19.6,
        "cost_usd": 0.21,
        "started_at": "09:58:52 AM",
    },
]

RUN_TRACE: dict[str, Any] = {
    "run_id": "run_01H7Z8K9",
    "name": "User",
    "kind": "user",
    "duration_s": None,
    "children": [
        {
            "name": "Supervisor",
            "kind": "pattern",
            "duration_s": 18.4,
            "children": [
                {"name": "Classifier", "kind": "agent", "duration_s": 2.1, "children": []},
                {"name": "Billing Agent", "kind": "agent", "duration_s": 9.8, "children": []},
                {"name": "Policy Checker", "kind": "tool", "duration_s": 1.2, "children": []},
            ],
        },
        {"name": "Response", "kind": "provider", "duration_s": 1.3, "children": []},
    ],
}

COST_OVER_TIME: list[dict[str, Any]] = [
    {"label": "09:00", "cost_usd": 0.0},
    {"label": "09:15", "cost_usd": 4.1},
    {"label": "09:30", "cost_usd": 9.8},
    {"label": "09:37", "cost_usd": 18.42},
    {"label": "09:45", "cost_usd": 22.3},
    {"label": "10:00", "cost_usd": 30.0},
]

COST_BREAKDOWN: list[dict[str, Any]] = [
    {"provider": "Anthropic", "cost_usd": 68.21, "pct": 54.8},
    {"provider": "OpenAI", "cost_usd": 38.32, "pct": 30.7},
    {"provider": "Google", "cost_usd": 11.45, "pct": 9.2},
    {"provider": "Others", "cost_usd": 6.60, "pct": 5.3},
]

TOP_AGENTS_BY_COST: list[dict[str, Any]] = [
    {"agent_name": "Billing Agent", "cost_usd": 42.31},
    {"agent_name": "Classifier", "cost_usd": 18.74},
    {"agent_name": "Policy Checker", "cost_usd": 12.11},
    {"agent_name": "Technical Agent", "cost_usd": 10.32},
    {"agent_name": "Other Agents", "cost_usd": 9.10},
]

PROVIDER_HEALTH: list[dict[str, Any]] = [
    {"provider": "Anthropic", "success_rate": 99.2, "latency_ms": 215},
    {"provider": "OpenAI", "success_rate": 98.7, "latency_ms": 342},
    {"provider": "Google", "success_rate": 99.1, "latency_ms": 289},
    {"provider": "Mistral AI", "success_rate": 95.3, "latency_ms": 512},
]
