"""Tests for WorkingMemory, SessionMemory, SemanticMemory."""

from __future__ import annotations

import tempfile

from pyagent_context.item import ContextItem
from pyagent_context.memory.semantic import InMemorySemanticStore
from pyagent_context.memory.session import SessionMemory
from pyagent_context.memory.working import WorkingMemory

# ── WorkingMemory ─────────────────────────────────────────────────────


def test_working_memory_add() -> None:
    wm = WorkingMemory(max_items=10, max_tokens=5000)
    item = ContextItem(content="hello", source="test")
    evicted = wm.add(item)
    assert len(wm) == 1
    assert evicted == []


def test_working_memory_evict_by_count() -> None:
    wm = WorkingMemory(max_items=2, max_tokens=100_000)
    wm.add(ContextItem(content="first", source="s"))
    wm.add(ContextItem(content="second", source="s"))
    evicted = wm.add(ContextItem(content="third", source="s"))
    assert len(wm) == 2
    assert len(evicted) == 1
    assert evicted[0].content == "first"


def test_working_memory_evict_by_tokens() -> None:
    wm = WorkingMemory(max_items=100, max_tokens=10)
    wm.add(ContextItem(content="a" * 20, source="s"))  # 5 tokens
    wm.add(ContextItem(content="b" * 20, source="s"))  # 5 tokens
    evicted = wm.add(ContextItem(content="c" * 20, source="s"))  # 5 tokens, total would be 15
    assert wm.total_tokens <= 10
    assert len(evicted) >= 1


def test_working_memory_utilization() -> None:
    wm = WorkingMemory(max_items=100, max_tokens=100)
    wm.add(ContextItem(content="a" * 100, source="s"))  # 25 tokens
    assert 0.2 <= wm.utilization <= 0.3


# ── SessionMemory (JSON) ─────────────────────────────────────────────


def test_session_memory_json_persist() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        sm = SessionMemory("test-session", backend="json", storage_path=tmpdir)
        sm.add(ContextItem(content="fact 1", source="agent"))
        sm.add(ContextItem(content="fact 2", source="agent"))
        sm.save()

        sm2 = SessionMemory("test-session", backend="json", storage_path=tmpdir)
        sm2.load()
        items = sm2.get_all()
        assert len(items) == 2
        assert items[0].content == "fact 1"


def test_session_memory_json_clear() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        sm = SessionMemory("test-session", backend="json", storage_path=tmpdir)
        sm.add(ContextItem(content="temp", source="s"))
        sm.save()
        sm.clear()
        assert len(sm) == 0


# ── SessionMemory (SQLite) ───────────────────────────────────────────


def test_session_memory_sqlite_persist() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        sm = SessionMemory("test-session", backend="sqlite", storage_path=tmpdir)
        sm.add(ContextItem(content="sqlite fact", source="agent"))
        sm.save()

        sm2 = SessionMemory("test-session", backend="sqlite", storage_path=tmpdir)
        sm2.load()
        items = sm2.get_all()
        assert len(items) == 1
        assert items[0].content == "sqlite fact"


# ── InMemorySemanticStore ────────────────────────────────────────────


def test_semantic_add_and_search() -> None:
    store = InMemorySemanticStore()
    store.add(ContextItem(content="Python asyncio event loop concurrency", source="docs"))
    store.add(ContextItem(content="JavaScript React component lifecycle", source="docs"))
    store.add(ContextItem(content="Python FastAPI web framework REST API", source="docs"))

    results = store.search("Python async web")
    assert len(results) > 0
    # Python items should score higher
    assert (
        "python" in results[0].item.content.lower() or "python" in results[0].item.content.lower()
    )


def test_semantic_remove() -> None:
    store = InMemorySemanticStore()
    item = ContextItem(content="removable content", source="s")
    store.add(item)
    assert len(store) == 1
    assert store.remove(item.id) is True
    assert len(store) == 0
    assert store.remove("nonexistent") is False


def test_semantic_clear() -> None:
    store = InMemorySemanticStore()
    store.add(ContextItem(content="a", source="s"))
    store.add(ContextItem(content="b", source="s"))
    store.clear()
    assert len(store) == 0


def test_semantic_empty_search() -> None:
    store = InMemorySemanticStore()
    results = store.search("anything")
    assert results == []
