"""RunsService: aggregate recorded pyagent-trace JSONL data into dashboard metrics."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from pyagent_studio.services import sample_data
from pyagent_studio.services.trace_service import TraceService, TraceSpan

_MODEL_PROVIDER_PREFIXES: list[tuple[str, str]] = [
    ("gpt-", "OpenAI"),
    ("o1", "OpenAI"),
    ("claude-", "Anthropic"),
    ("gemini-", "Google"),
    ("mistral-", "Mistral AI"),
    ("command-", "Cohere"),
    ("llama-", "Meta"),
]


def _provider_for_model(model: str) -> str:
    """Map a model identifier to a display provider name."""
    lower = model.lower()
    for prefix, provider in _MODEL_PROVIDER_PREFIXES:
        if lower.startswith(prefix):
            return provider
    return "Other"


def _parse_ts(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


@dataclass
class Run:
    """A single grouped workflow run."""

    run_id: str
    workflow: str
    status: str = "success"
    started_at: datetime | None = None
    ended_at: datetime | None = None
    cost_usd: float = 0.0
    tokens: int = 0
    children: list[dict[str, Any]] = field(default_factory=list)

    @property
    def duration_s(self) -> float:
        if self.started_at and self.ended_at:
            return max((self.ended_at - self.started_at).total_seconds(), 0.0)
        return 0.0


class RunsService:
    """Group raw trace spans into runs and compute dashboard metrics.

    Falls back to the bundled sample dataset whenever no trace file is
    loaded or the loaded file contains no recognizable runs.
    """

    def __init__(self) -> None:
        self._trace_service = TraceService()
        self._path: Path | None = None
        self._mtime: float | None = None
        self._runs: list[Run] = []
        self._cost_records: list[dict[str, Any]] = []
        self._llm_calls: list[dict[str, Any]] = []
        self._errors: list[dict[str, Any]] = []

    def load(self, path: str | Path) -> None:
        """Load and parse a trace JSONL file."""
        self._path = Path(path)
        spans = self._trace_service.load(self._path)
        self._mtime = self._path.stat().st_mtime
        self._build(spans)

    def reload_if_stale(self) -> None:
        """Re-parse the trace file if it changed on disk since the last load."""
        if self._path is None or not self._path.exists():
            return
        mtime = self._path.stat().st_mtime
        if mtime != self._mtime:
            self.load(self._path)

    @property
    def is_loaded(self) -> bool:
        return bool(self._runs)

    def _build(self, spans: list[TraceSpan]) -> None:
        self._runs = []
        self._cost_records = []
        self._llm_calls = []
        self._errors = []

        current: Run | None = None
        for span in spans:
            data = span.data
            if span.event_type == "pattern_start":
                current = Run(
                    run_id=data.get("run_id", f"run_{len(self._runs)}"),
                    workflow=data.get("workflow", data.get("pattern_type", "workflow")),
                    started_at=_parse_ts(span.timestamp),
                )
            elif span.event_type == "pattern_end" and current is not None:
                current.status = data.get("status", "success")
                current.ended_at = _parse_ts(span.timestamp)
                self._runs.append(current)
                current = None
            elif span.event_type == "agent_start" and current is not None:
                current.children.append(
                    {
                        "name": span.agent_name,
                        "kind": data.get("kind", "agent"),
                        "_started": _parse_ts(span.timestamp),
                        "duration_s": 0.0,
                    }
                )
            elif span.event_type == "agent_end" and current is not None:
                ended = _parse_ts(span.timestamp)
                for child in reversed(current.children):
                    if child["name"] == span.agent_name and child["duration_s"] == 0.0:
                        started = child.pop("_started", None)
                        if started and ended:
                            child["duration_s"] = max((ended - started).total_seconds(), 0.0)
                        break
            elif span.event_type == "llm_call":
                self._llm_calls.append(
                    {
                        "agent_name": span.agent_name,
                        "model": data.get("model", ""),
                        "duration_ms": span.duration_ms,
                        "timestamp": span.timestamp,
                    }
                )
            elif span.event_type == "cost_record":
                record = {
                    "agent_name": span.agent_name or data.get("agent_name", ""),
                    "model": data.get("model", ""),
                    "pattern_type": data.get("pattern_type", ""),
                    "cost_usd": float(data.get("cost_usd", 0.0)),
                    "tokens": int(data.get("input_tokens", 0)) + int(data.get("output_tokens", 0)),
                    "timestamp": span.timestamp,
                }
                self._cost_records.append(record)
                if current is not None:
                    current.cost_usd += record["cost_usd"]
                    current.tokens += record["tokens"]
            elif span.event_type == "error":
                self._errors.append(
                    {
                        "agent_name": span.agent_name,
                        "model": data.get("model", ""),
                        "timestamp": span.timestamp,
                    }
                )

        for run in self._runs:
            for child in run.children:
                child.pop("_started", None)

    # --- Metrics -----------------------------------------------------

    def _kpis(self) -> dict[str, dict[str, Any]]:
        runs = self._runs
        total_runs = len(runs)
        successes = sum(1 for r in runs if r.status == "success")
        success_rate = (successes / total_runs * 100) if total_runs else 0.0
        total_cost = sum(r.cost_usd for r in runs)
        total_tokens = sum(r.tokens for r in runs)
        avg_latency_ms = (
            sum(c["duration_ms"] for c in self._llm_calls) / len(self._llm_calls)
            if self._llm_calls
            else 0.0
        )

        # Split runs into two equal-length time windows around the midpoint of
        # the trace's time range, so deltas compare a real "previous period".
        timed = sorted((r for r in runs if r.started_at), key=lambda r: r.started_at)
        prev_runs: list[Run] = []
        curr_runs: list[Run] = []
        if len(timed) >= 2:
            start, end = timed[0].started_at, timed[-1].started_at
            midpoint = start + (end - start) / 2
            for run in timed:
                (prev_runs if run.started_at < midpoint else curr_runs).append(run)

        def _delta(curr: float, prev: float) -> float | None:
            if not prev_runs or not curr_runs or not prev:
                return None
            return round((curr - prev) / prev * 100, 1)

        def _rate(window: list[Run]) -> float:
            return (sum(1 for r in window if r.status == "success") / len(window) * 100) if window else 0.0

        delta_label = "vs previous period"

        return {
            "total_runs": {
                "label": "Total Runs",
                "value": f"{total_runs:,}",
                "delta_pct": _delta(len(curr_runs), len(prev_runs)),
                "delta_label": delta_label,
                "direction": "up",
            },
            "success_rate": {
                "label": "Success Rate",
                "value": f"{success_rate:.1f}%",
                "delta_pct": _delta(_rate(curr_runs), _rate(prev_runs)),
                "delta_label": delta_label,
                "direction": "up",
            },
            "total_cost": {
                "label": "Total Cost",
                "value": f"${total_cost:,.2f}",
                "delta_pct": _delta(
                    sum(r.cost_usd for r in curr_runs), sum(r.cost_usd for r in prev_runs)
                ),
                "delta_label": delta_label,
                "direction": "down",
            },
            "total_tokens": {
                "label": "Total Tokens",
                "value": f"{total_tokens:,}",
                "delta_pct": _delta(
                    sum(r.tokens for r in curr_runs), sum(r.tokens for r in prev_runs)
                ),
                "delta_label": delta_label,
                "direction": "down",
            },
            "avg_latency": {
                "label": "Avg Latency",
                "value": f"{avg_latency_ms / 1000:.2f}s",
                "delta_pct": None,
                "delta_label": delta_label,
                "direction": "down",
            },
        }

    def _recent_runs(self, limit: int = 5) -> list[dict[str, Any]]:
        rows = []
        for run in sorted(self._runs, key=lambda r: r.started_at or datetime.min, reverse=True)[:limit]:
            rows.append(
                {
                    "run_id": run.run_id,
                    "workflow": run.workflow,
                    "status": run.status,
                    "duration_s": round(run.duration_s, 1),
                    "cost_usd": round(run.cost_usd, 4),
                    "started_at": run.started_at.strftime("%I:%M:%S %p") if run.started_at else "-",
                }
            )
        return rows

    def _run_trace(self, run_id: str | None = None) -> dict[str, Any]:
        target = next((r for r in self._runs if r.run_id == run_id), None) if run_id else None
        target = target or (self._runs[-1] if self._runs else None)
        if target is None:
            return sample_data.RUN_TRACE

        return {
            "run_id": target.run_id,
            "name": "User",
            "kind": "user",
            "duration_s": None,
            "children": [
                {
                    "name": target.workflow,
                    "kind": "pattern",
                    "duration_s": round(target.duration_s, 1),
                    "children": [
                        {
                            "name": c["name"],
                            "kind": c["kind"],
                            "duration_s": round(c["duration_s"], 1),
                            "children": [],
                        }
                        for c in target.children
                    ],
                },
                {"name": "Response", "kind": "provider", "duration_s": 0.0, "children": []},
            ],
        }

    def _cost_over_time(self, buckets: int = 12) -> list[dict[str, Any]]:
        """Cumulative cost across ``buckets`` evenly-spaced time intervals."""
        parsed = [
            (_parse_ts(r["timestamp"]), r["cost_usd"]) for r in self._cost_records
        ]
        parsed = [(ts, cost) for ts, cost in parsed if ts is not None]
        if not parsed:
            return []
        parsed.sort(key=lambda x: x[0])

        start, end = parsed[0][0], parsed[-1][0]
        span = (end - start).total_seconds()
        if span <= 0:
            total = sum(cost for _, cost in parsed)
            return [{"label": start.strftime("%H:%M"), "cost_usd": round(total, 4)}]

        bucket_seconds = span / buckets
        bucket_totals = [0.0] * buckets
        for ts, cost in parsed:
            idx = min(int((ts - start).total_seconds() / span * buckets), buckets - 1)
            bucket_totals[idx] += cost

        cumulative = 0.0
        points: list[dict[str, Any]] = []
        for i in range(buckets):
            cumulative += bucket_totals[i]
            label = (start + timedelta(seconds=bucket_seconds * i)).strftime("%H:%M")
            points.append({"label": label, "cost_usd": round(cumulative, 4)})
        return points

    def _cost_breakdown_by_provider(self) -> list[dict[str, Any]]:
        totals: dict[str, float] = {}
        for record in self._cost_records:
            provider = _provider_for_model(record["model"])
            totals[provider] = totals.get(provider, 0.0) + record["cost_usd"]
        grand_total = sum(totals.values())
        if not grand_total:
            return []
        return [
            {
                "provider": provider,
                "cost_usd": round(cost, 4),
                "pct": round(cost / grand_total * 100, 1),
            }
            for provider, cost in sorted(totals.items(), key=lambda kv: kv[1], reverse=True)
        ]

    def _top_agents_by_cost(self, limit: int = 5) -> list[dict[str, Any]]:
        totals: dict[str, float] = {}
        for record in self._cost_records:
            name = record["agent_name"] or "unknown"
            totals[name] = totals.get(name, 0.0) + record["cost_usd"]
        ranked = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)[:limit]
        return [{"agent_name": name, "cost_usd": round(cost, 4)} for name, cost in ranked]

    def _provider_health(self) -> list[dict[str, Any]]:
        calls_by_provider: dict[str, int] = {}
        errors_by_provider: dict[str, int] = {}
        latency_by_provider: dict[str, list[float]] = {}

        for call in self._llm_calls:
            provider = _provider_for_model(call["model"])
            calls_by_provider[provider] = calls_by_provider.get(provider, 0) + 1
            latency_by_provider.setdefault(provider, []).append(call["duration_ms"])
        for error in self._errors:
            provider = _provider_for_model(error["model"])
            errors_by_provider[provider] = errors_by_provider.get(provider, 0) + 1
            calls_by_provider.setdefault(provider, 0)

        rows = []
        for provider, calls in calls_by_provider.items():
            errors = errors_by_provider.get(provider, 0)
            success_rate = ((calls - errors) / calls * 100) if calls else 0.0
            latencies = latency_by_provider.get(provider, [])
            avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
            rows.append(
                {
                    "provider": provider,
                    "success_rate": round(success_rate, 1),
                    "latency_ms": round(avg_latency),
                }
            )
        return sorted(rows, key=lambda r: r["provider"])

    def dashboard_context(self) -> dict[str, Any]:
        """Build the full Overview page context, falling back to sample data."""
        self.reload_if_stale()

        if not self.is_loaded:
            return {
                "kpis": sample_data.KPIS,
                "recent_runs": sample_data.RECENT_RUNS,
                "run_trace": sample_data.RUN_TRACE,
                "cost_over_time": sample_data.COST_OVER_TIME,
                "cost_breakdown": sample_data.COST_BREAKDOWN,
                "top_agents": sample_data.TOP_AGENTS_BY_COST,
                "provider_health": sample_data.PROVIDER_HEALTH,
                "using_sample_data": True,
            }

        cost_over_time = self._cost_over_time()
        cost_breakdown = self._cost_breakdown_by_provider()
        top_agents = self._top_agents_by_cost()
        provider_health = self._provider_health()

        return {
            "kpis": self._kpis(),
            "recent_runs": self._recent_runs(),
            "run_trace": self._run_trace(),
            "cost_over_time": cost_over_time or sample_data.COST_OVER_TIME,
            "cost_breakdown": cost_breakdown or sample_data.COST_BREAKDOWN,
            "top_agents": top_agents or sample_data.TOP_AGENTS_BY_COST,
            "provider_health": provider_health or sample_data.PROVIDER_HEALTH,
            "using_sample_data": False,
        }
