"""Syntax-check every ``python`` fenced code block under ``docs/``.

This is the first layer of docs validation: extract each fenced Python block
from the Markdown sources and attempt to :func:`compile` it, failing loudly
(with file path and block index) on any :class:`SyntaxError`.

Scope and limitations — read before trusting a green run:

* :func:`compile` only parses; it does **not** execute. So this catches
  syntax errors (unbalanced parens, bad indentation, malformed f-strings) but
  **not** semantic errors such as calling a function with a kwarg that does not
  exist, importing a missing symbol, or a wrong argument type. Those need an
  import/execute layer, which this test deliberately does not attempt (most doc
  snippets are partial and make live LLM calls).
* Blocks are line-anchored per CommonMark: a fence is only a fence at the start
  of a line (after optional indentation), matching how MkDocs parses them. A
  triple-backtick that appears mid-line inside a string literal is therefore
  correctly treated as code, not as a fence terminator.
* Blocks are :func:`textwrap.dedent`-ed first, so snippets nested inside
  admonitions or tabbed content (uniformly indented) are not false-positives.
* Top-level ``await`` is allowed (``PyCF_ALLOW_TOP_LEVEL_AWAIT``): docs use
  REPL/notebook-style snippets where top-level ``await`` is idiomatic.
"""

from __future__ import annotations

import ast
import re
import textwrap
from pathlib import Path

import pytest

DOCS_DIR = Path(__file__).resolve().parents[2] / "docs"

_FENCE = re.compile(r"^(?P<indent>[ \t]*)(?P<ticks>`{3,})[ \t]*(?P<info>[^\n`]*)$")
_ALLOW_TOP_LEVEL_AWAIT = ast.PyCF_ALLOW_TOP_LEVEL_AWAIT


def _extract_python_blocks(text: str) -> list[str]:
    """Return the source of every ``python``/``py`` fenced block in ``text``.

    Line-based parser that honours variable-length fences (``` vs ````), so an
    outer block may legitimately contain shorter backtick runs in its content.
    """
    lines = text.splitlines()
    blocks: list[str] = []
    i = 0
    while i < len(lines):
        opener = _FENCE.match(lines[i])
        if not opener:
            i += 1
            continue
        ticks = opener.group("ticks")
        indent = opener.group("indent")
        info = opener.group("info").strip().lower()
        body: list[str] = []
        i += 1
        while i < len(lines):
            closer = _FENCE.match(lines[i])
            if (
                closer
                and closer.group("ticks")[0] == ticks[0]
                and len(closer.group("ticks")) >= len(ticks)
                and closer.group("info").strip() == ""
            ):
                break
            line = lines[i]
            body.append(line[len(indent) :] if line.startswith(indent) else line)
            i += 1
        if info.split() and info.split()[0] in ("python", "py"):
            blocks.append("\n".join(body))
        i += 1
    return blocks


def _discover() -> list[tuple[str, int, str]]:
    """Collect ``(relative_path, block_index, source)`` for every python block."""
    found: list[tuple[str, int, str]] = []
    for md in sorted(DOCS_DIR.rglob("*.md")):
        rel = md.relative_to(DOCS_DIR).as_posix()
        for idx, block in enumerate(_extract_python_blocks(md.read_text(encoding="utf-8"))):
            found.append((rel, idx, textwrap.dedent(block)))
    return found


_BLOCKS = _discover()


def test_docs_dir_exists() -> None:
    assert DOCS_DIR.is_dir(), f"docs directory not found at {DOCS_DIR}"


def test_found_some_python_blocks() -> None:
    # Guard against the extractor silently matching nothing (e.g. a refactor
    # that breaks discovery), which would make every check vacuously pass.
    assert _BLOCKS, "no python code blocks discovered under docs/"


@pytest.mark.parametrize(
    ("rel_path", "index", "source"),
    _BLOCKS,
    ids=[f"{rel}#{idx}" for rel, idx, _ in _BLOCKS],
)
def test_python_block_compiles(rel_path: str, index: int, source: str) -> None:
    try:
        compile(source, f"docs/{rel_path}#block{index}", "exec", flags=_ALLOW_TOP_LEVEL_AWAIT)
    except SyntaxError as exc:  # pragma: no cover - failure path
        pytest.fail(
            f"SyntaxError in docs/{rel_path} python block #{index} "
            f"(line {exc.lineno}): {exc.msg}\n"
            f"--- block source ---\n{source}"
        )
