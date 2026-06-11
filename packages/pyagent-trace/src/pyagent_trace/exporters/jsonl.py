"""JsonlExporter — writes trace events to JSONL files."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import IO

from pyagent_trace.events import TraceEvent


class JsonlExporter:
    """Export trace events to a JSONL file.

    Usage:
        exporter = JsonlExporter("traces/run_001.jsonl")
        bus.subscribe(exporter.export_event)
    """

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._file: IO[str] | None = None

    def _ensure_open(self) -> IO[str]:
        if self._file is None or self._file.closed:
            self._file = self._path.open("a")
        return self._file

    def export_event(self, event: TraceEvent) -> None:
        """Append a trace event as a JSON line."""
        f = self._ensure_open()
        f.write(json.dumps(asdict(event), default=str) + "\n")

    def flush(self) -> None:
        """Flush buffered writes to disk."""
        if self._file and not self._file.closed:
            self._file.flush()

    def shutdown(self) -> None:
        """Flush and close the file."""
        if self._file and not self._file.closed:
            self._file.flush()
            self._file.close()
