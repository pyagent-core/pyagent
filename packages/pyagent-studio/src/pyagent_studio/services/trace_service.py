"""TraceService: load and query recorded trace JSONL files."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class TraceSpan:
    """A single trace span from a recorded session.

    Attributes:
        event_type: Type of event (e.g., 'llm_call', 'pattern_start').
        agent_name: Agent that produced this span.
        timestamp: ISO timestamp string.
        duration_ms: Duration in milliseconds.
        tokens: Token count (if applicable).
        data: Full event data dict.
    """

    event_type: str
    agent_name: str = ""
    timestamp: str = ""
    duration_ms: float = 0.0
    tokens: int = 0
    data: dict[str, Any] = field(default_factory=dict)


class TraceService:
    """Load and query trace JSONL files from pyagent-trace Recorder.

    Each line in a JSONL file is a JSON object representing a trace event.
    """

    def __init__(self) -> None:
        self._spans: list[TraceSpan] = []
        self._path: Path | None = None

    def load(self, path: str | Path) -> list[TraceSpan]:
        """Load spans from a JSONL file.

        Args:
            path: Path to ``.jsonl`` trace file.

        Returns:
            List of parsed ``TraceSpan`` objects.

        Raises:
            FileNotFoundError: If file doesn't exist.
        """
        self._path = Path(path)
        if not self._path.exists():
            raise FileNotFoundError(f"Trace file not found: {self._path}")

        self._spans = []
        for line in self._path.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                span = TraceSpan(
                    event_type=data.get("event_type", data.get("type", "unknown")),
                    agent_name=data.get("agent_name", data.get("agent", "")),
                    timestamp=data.get("timestamp", ""),
                    duration_ms=data.get("duration_ms", 0.0),
                    tokens=data.get("tokens", data.get("token_count", 0)),
                    data=data,
                )
                self._spans.append(span)
            except json.JSONDecodeError:
                continue

        return self._spans

    def query(
        self,
        event_type: str | None = None,
        agent_name: str | None = None,
    ) -> list[TraceSpan]:
        """Filter loaded spans.

        Args:
            event_type: Filter by event type.
            agent_name: Filter by agent name.

        Returns:
            Filtered list of spans.
        """
        results = self._spans
        if event_type:
            results = [s for s in results if s.event_type == event_type]
        if agent_name:
            results = [s for s in results if s.agent_name == agent_name]
        return results

    @property
    def spans(self) -> list[TraceSpan]:
        return list(self._spans)

    def summary(self) -> dict[str, Any]:
        """Summary statistics for loaded traces."""
        if not self._spans:
            return {"loaded": False, "count": 0}
        return {
            "loaded": True,
            "count": len(self._spans),
            "event_types": sorted({s.event_type for s in self._spans}),
            "agents": sorted({s.agent_name for s in self._spans if s.agent_name}),
            "total_tokens": sum(s.tokens for s in self._spans),
            "total_duration_ms": sum(s.duration_ms for s in self._spans),
        }
