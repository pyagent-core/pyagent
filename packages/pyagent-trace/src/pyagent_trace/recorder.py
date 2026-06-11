"""Recorder: serialize all pattern messages and LLM responses for replay/debug.

Record mode: saves all messages + LLM responses to a JSONL file.
Replay mode: re-runs pattern with recorded LLM responses (deterministic).
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pyagent_patterns.base import Message
    from pyagent_trace.events import TraceEventBus


@dataclass
class RecordEntry:
    """A single recorded event."""

    timestamp: float
    event_type: str  # "llm_call", "message", "pattern_start", "pattern_end"
    agent_name: str
    messages_in: list[dict[str, Any]]
    response: str
    metadata: dict[str, Any]


class Recorder:
    """Record pattern executions for debugging and replay.

    Usage:
        recorder = Recorder()
        recorder.start("debate")
        recorder.record_llm_call("bull", messages, response)
        recorder.save("debug_trace.jsonl")
    """

    def __init__(self, event_bus: TraceEventBus | None = None) -> None:
        self._entries: list[RecordEntry] = []
        self._start_time: float = 0.0
        self._event_bus = event_bus

    def start(self, pattern_type: str) -> None:
        """Mark the start of a pattern execution."""
        self._start_time = time.time()
        self._entries.append(
            RecordEntry(
                timestamp=self._start_time,
                event_type="pattern_start",
                agent_name="",
                messages_in=[],
                response="",
                metadata={"pattern_type": pattern_type},
            )
        )
        if self._event_bus:
            from pyagent_trace.events import TraceEvent

            self._event_bus.emit(
                TraceEvent(
                    timestamp=self._start_time,
                    event_type="pattern_start",
                    pattern_type=pattern_type,
                    payload={"pattern_type": pattern_type},
                )
            )

    def record_llm_call(
        self,
        agent_name: str,
        messages: list[Message],
        response: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Record an LLM call and its response."""
        ts = time.time()
        meta = metadata or {}
        self._entries.append(
            RecordEntry(
                timestamp=ts,
                event_type="llm_call",
                agent_name=agent_name,
                messages_in=[
                    {"role": m.role.value, "content": m.content, "name": m.name} for m in messages
                ],
                response=response,
                metadata=meta,
            )
        )
        if self._event_bus:
            from pyagent_trace.events import TraceEvent

            self._event_bus.emit(
                TraceEvent(
                    timestamp=ts,
                    event_type="llm_call",
                    agent_name=agent_name,
                    payload={
                        "response": response,
                        "model": meta.get("model", ""),
                        **meta,
                    },
                )
            )

    def end(self, result_output: str) -> None:
        """Mark the end of a pattern execution."""
        ts = time.time()
        duration = ts - self._start_time
        self._entries.append(
            RecordEntry(
                timestamp=ts,
                event_type="pattern_end",
                agent_name="",
                messages_in=[],
                response=result_output,
                metadata={"duration_seconds": duration},
            )
        )
        if self._event_bus:
            from pyagent_trace.events import TraceEvent

            self._event_bus.emit(
                TraceEvent(
                    timestamp=ts,
                    event_type="pattern_end",
                    payload={
                        "result_output": result_output,
                        "duration_seconds": duration,
                    },
                )
            )

    def save(self, path: str | Path) -> None:
        """Save recorded entries to a JSONL file."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("w") as f:
            for entry in self._entries:
                f.write(json.dumps(asdict(entry), default=str) + "\n")

    @classmethod
    def load(cls, path: str | Path) -> list[RecordEntry]:
        """Load recorded entries from a JSONL file."""
        entries: list[RecordEntry] = []
        with Path(path).open() as f:
            for line in f:
                data = json.loads(line.strip())
                entries.append(RecordEntry(**data))
        return entries

    @property
    def entries(self) -> list[RecordEntry]:
        return list(self._entries)

    @property
    def llm_calls(self) -> list[RecordEntry]:
        return [e for e in self._entries if e.event_type == "llm_call"]
