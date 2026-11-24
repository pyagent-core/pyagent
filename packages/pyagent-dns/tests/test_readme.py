"""The README's Python blocks are run in order, so the quickstart cannot drift from the API."""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pyagent_dns.authority import Outcome
from pyagent_dns.signing import VerificationStatus

if TYPE_CHECKING:
    import pytest

README = Path(__file__).parent.parent / "README.md"


def python_blocks() -> list[str]:
    return re.findall(r"```python\n(.*?)```", README.read_text(encoding="utf-8"), flags=re.DOTALL)


def test_the_readme_has_runnable_examples() -> None:
    assert len(python_blocks()) >= 5


def test_the_readme_quickstart_runs_and_says_what_it_claims(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)  # the quickstart writes ./.keys
    namespace: dict[str, Any] = {}
    for index, block in enumerate(python_blocks()):
        try:
            exec(compile(block, f"README.md[python block {index}]", "exec"), namespace)
        except Exception as exc:
            raise AssertionError(f"README python block {index} failed: {exc!r}\n{block}") from exc

    assert namespace["resolution"].verification == VerificationStatus.VERIFIED
    assert namespace["decision"].allowed
    assert namespace["decision"].outcome in (Outcome.ALLOW, Outcome.ALLOW_WITH_OBLIGATIONS)
    decisions = namespace["middleware"].decisions
    assert [d.reason_code for d in decisions] == ["GRANT_FOUND", "NO_GRANT"]
    assert (tmp_path / ".keys" / "private_key.pem").exists()

    printed = capsys.readouterr().out
    for claim in (
        "verified",
        "True GRANT_FOUND",
        "positions: AAPL, GOOG",
        "DENIED [NO_GRANT]",
        "100",
        "Refused widening on: limits.max_records_per_call",
    ):
        assert claim in printed, claim
