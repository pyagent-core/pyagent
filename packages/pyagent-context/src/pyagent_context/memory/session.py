"""SessionMemory: persisted across turns via JSON file or SQLite."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from pyagent_context.item import ContextItem


class SessionMemory:
    """Session-scoped memory that persists across turns.

    Supports two backends:
    - ``json``: simple JSON file per session (default)
    - ``sqlite``: SQLite database for concurrent-safe access

    Args:
        session_id: Unique session identifier.
        backend: ``"json"`` or ``"sqlite"``.
        storage_path: Directory for storage files. Defaults to ``".pyagent_sessions"``.
    """

    def __init__(
        self,
        session_id: str,
        backend: str = "json",
        storage_path: str | Path = ".pyagent_sessions",
    ) -> None:
        self._session_id = session_id
        self._backend = backend
        self._storage_path = Path(storage_path)
        self._storage_path.mkdir(parents=True, exist_ok=True)
        self._items: list[ContextItem] = []
        self._loaded = False

    @property
    def session_id(self) -> str:
        return self._session_id

    def add(self, item: ContextItem) -> None:
        """Add an item to the session."""
        self._ensure_loaded()
        self._items.append(item)

    def get_all(self) -> list[ContextItem]:
        """Return all items in this session."""
        self._ensure_loaded()
        return list(self._items)

    def save(self) -> None:
        """Persist current items to storage."""
        if self._backend == "sqlite":
            self._save_sqlite()
        else:
            self._save_json()

    def load(self) -> None:
        """Load items from storage."""
        if self._backend == "sqlite":
            self._load_sqlite()
        else:
            self._load_json()
        self._loaded = True

    def clear(self) -> None:
        """Remove all items and delete persisted data."""
        self._items.clear()
        path = self._file_path
        if path.exists():
            path.unlink()

    # ------------------------------------------------------------------
    # JSON backend
    # ------------------------------------------------------------------

    def _save_json(self) -> None:
        path = self._file_path
        data = [item.to_dict() for item in self._items]
        path.write_text(json.dumps(data, indent=2))

    def _load_json(self) -> None:
        path = self._file_path
        if path.exists():
            data = json.loads(path.read_text())
            self._items = [ContextItem.from_dict(d) for d in data]
        else:
            self._items = []

    # ------------------------------------------------------------------
    # SQLite backend
    # ------------------------------------------------------------------

    def _save_sqlite(self) -> None:
        db_path = self._storage_path / "sessions.db"
        conn = sqlite3.connect(str(db_path))
        try:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS context_items "
                "(session_id TEXT, item_id TEXT PRIMARY KEY, data TEXT)"
            )
            conn.execute(
                "DELETE FROM context_items WHERE session_id = ?",
                (self._session_id,),
            )
            for item in self._items:
                conn.execute(
                    "INSERT INTO context_items (session_id, item_id, data) VALUES (?, ?, ?)",
                    (self._session_id, item.id, json.dumps(item.to_dict())),
                )
            conn.commit()
        finally:
            conn.close()

    def _load_sqlite(self) -> None:
        db_path = self._storage_path / "sessions.db"
        if not db_path.exists():
            self._items = []
            return
        conn = sqlite3.connect(str(db_path))
        try:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS context_items "
                "(session_id TEXT, item_id TEXT PRIMARY KEY, data TEXT)"
            )
            cursor = conn.execute(
                "SELECT data FROM context_items WHERE session_id = ? ORDER BY rowid",
                (self._session_id,),
            )
            self._items = [ContextItem.from_dict(json.loads(row[0])) for row in cursor]
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @property
    def _file_path(self) -> Path:
        suffix = ".db" if self._backend == "sqlite" else ".json"
        return self._storage_path / f"{self._session_id}{suffix}"

    def _ensure_loaded(self) -> None:
        if not self._loaded:
            self.load()

    def __len__(self) -> int:
        self._ensure_loaded()
        return len(self._items)
