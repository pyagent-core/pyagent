"""Tests for NameRecord, Identity, version ordering, and the record file loaders."""

from __future__ import annotations

import dataclasses
import json
import time
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from pyagent_dns.records import (
    Identity,
    NameRecord,
    RecordKind,
    RecordLoadError,
    RecordStatus,
    ensure_aware,
    load_records_directory,
    load_records_file,
    parse_expiry,
    version_key,
)

if TYPE_CHECKING:
    from collections.abc import Callable

FIXTURES = Path(__file__).parent / "fixtures"


def raw(**overrides: Any) -> dict[str, Any]:
    """A valid record mapping, as it would appear in a YAML file."""
    base: dict[str, Any] = {
        "name": "portfolio-data.reader",
        "kind": "tool",
        "version": "3.2.1",
        "endpoint": "https://internal.example/portfolio",
        "identity": {
            "public_key_fingerprint": "sha256:" + "11" * 32,
            "signed_by": "platform_registry",
        },
        "schema_hash": "sha256:" + "22" * 32,
        "capabilities": ["read_positions"],
        "data_classes": ["internal"],
        "owner": "wealth_platform_team",
    }
    return base | overrides


# -- Canonical form and fingerprints ---------------------------------------------------------


def test_canonical_bytes_do_not_depend_on_the_key_order_of_the_source_file(tmp_path: Path) -> None:
    forward = tmp_path / "forward.yaml"
    reverse = tmp_path / "reverse.yaml"
    forward.write_text(
        "name: x.tool\nkind: tool\nversion: 1.0.0\nendpoint: e\nschema_hash: s\nowner: o\n"
        "capabilities: [a, b]\ndata_classes: [internal]\nidentity: {public_key_fingerprint: f}\n"
    )
    reverse.write_text(
        "identity: {public_key_fingerprint: f}\ndata_classes: [internal]\ncapabilities: [a, b]\n"
        "owner: o\nschema_hash: s\nendpoint: e\nversion: 1.0.0\nkind: tool\nname: x.tool\n"
    )
    assert (
        load_records_file(forward)[0].canonical_bytes()
        == load_records_file(reverse)[0].canonical_bytes()
    )


def test_canonical_bytes_are_the_same_on_every_host_timezone(
    make_record: Callable[..., NameRecord], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Same record, same bytes, wherever it is verified. The expiry is written in +05:30."""
    expiry = datetime(2030, 1, 1, 12, 0, tzinfo=timezone(timedelta(hours=5, minutes=30)))
    record = make_record(expires=expiry)
    results = set()
    for tz in ("America/New_York", "Asia/Tokyo", "UTC"):
        monkeypatch.setenv("TZ", tz)
        time.tzset()
        results.add(record.canonical_bytes())
    monkeypatch.undo()
    time.tzset()
    assert len(results) == 1
    assert b'"expires":"2030-01-01T06:30:00Z"' in results.pop()


def test_canonical_bytes_include_the_domain_separator_and_exclude_the_signature(
    make_record: Callable[..., NameRecord],
) -> None:
    payload = json.loads(make_record().canonical_bytes())
    assert payload["_pyagent_dns"] == "record/v1"
    assert "signature" not in payload


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("endpoint", "https://elsewhere.example"),
        ("schema_hash", "sha256:" + "ff" * 32),
        ("capabilities", ("read_positions", "wire_funds")),
        ("data_classes", ("confidential",)),
        ("status", RecordStatus.DEPRECATED),
        ("version", "3.2.2"),
        ("owner", "someone_else"),
    ],
)
def test_the_fingerprint_changes_when_any_signed_field_changes(
    make_record: Callable[..., NameRecord], field: str, value: Any
) -> None:
    record = make_record()
    assert dataclasses.replace(record, **{field: value}).fingerprint != record.fingerprint


def test_the_fingerprint_ignores_the_signature(make_record: Callable[..., NameRecord]) -> None:
    assert make_record().fingerprint == make_record(sign=False).fingerprint


# -- Round trips -----------------------------------------------------------------------------


def test_a_record_survives_a_dict_round_trip_including_its_expiry_and_signature(
    make_record: Callable[..., NameRecord],
) -> None:
    record = make_record(expires=datetime(2031, 3, 4, 5, 6, 7, tzinfo=UTC))
    assert NameRecord.from_dict(record.to_dict()) == record


def test_no_expiry_round_trips_as_no_expiry(make_record: Callable[..., NameRecord]) -> None:
    again = NameRecord.from_dict(make_record().to_dict())
    assert again.expires is None
    assert not again.is_expired(datetime(2099, 1, 1, tzinfo=UTC))


# -- Expiry ----------------------------------------------------------------------------------


def test_a_bare_date_expiry_means_the_end_of_that_day_in_utc() -> None:
    from datetime import date

    expected = datetime(2026, 12, 31, 23, 59, 59, tzinfo=UTC)
    assert parse_expiry(date(2026, 12, 31), where="t", error=RecordLoadError) == expected
    assert parse_expiry("2026-12-31", where="t", error=RecordLoadError) == expected


@pytest.mark.parametrize(
    "value",
    [
        "2026-12-31T10:00:00Z",
        "2026-12-31T10:00:00+00:00",
        "2026-12-31T15:30:00+05:30",
        datetime(2026, 12, 31, 10, 0, 0),  # naive: read as UTC
        datetime(2026, 12, 31, 5, 0, 0, tzinfo=timezone(timedelta(hours=-5))),
    ],
)
def test_datetime_expiries_normalize_to_the_same_utc_instant(value: Any) -> None:
    parsed = parse_expiry(value, where="t", error=RecordLoadError)
    assert parsed == datetime(2026, 12, 31, 10, 0, 0, tzinfo=UTC)
    assert parsed.utcoffset() == timedelta(0)


@pytest.mark.parametrize("bad", ["next tuesday", 12345, ["2026-01-01"]])
def test_an_unparseable_expiry_is_an_error(bad: Any) -> None:
    with pytest.raises(RecordLoadError):
        parse_expiry(bad, where="t", error=RecordLoadError)


def test_a_naive_expiry_is_refused_when_building_a_record_in_code(
    make_record: Callable[..., NameRecord],
) -> None:
    """astimezone() would read a naive datetime in the host timezone, so signatures would differ per host."""
    with pytest.raises(ValueError, match="timezone-aware"):
        make_record(expires=datetime(2030, 1, 1, 12, 0))


def test_a_record_is_valid_through_its_expiry_instant_and_expired_after_it(
    make_record: Callable[..., NameRecord],
) -> None:
    """The boundary is part of the contract: `expires` is the last instant of validity."""
    expiry = datetime(2030, 1, 1, tzinfo=UTC)
    record = make_record(expires=expiry)
    assert not record.is_expired(expiry)
    assert record.is_expired(expiry + timedelta(microseconds=1))


def test_is_expired_compares_against_an_aware_now(make_record: Callable[..., NameRecord]) -> None:
    record = make_record(expires=datetime(2030, 1, 1, tzinfo=UTC))
    assert not record.is_expired(datetime(2029, 12, 31, tzinfo=UTC))
    assert record.is_expired(datetime(2030, 1, 1, 0, 0, 1, tzinfo=UTC))
    with pytest.raises(ValueError, match="timezone-aware"):
        record.is_expired(datetime(2029, 1, 1))


def test_ensure_aware_returns_aware_values_unchanged() -> None:
    value = datetime(2030, 1, 1, tzinfo=UTC)
    assert ensure_aware(value, "x") is value


# -- Immutability and validation -------------------------------------------------------------


def test_lists_become_tuples_so_a_signed_record_cannot_be_altered_through_them(
    make_record: Callable[..., NameRecord],
) -> None:
    shared = ["read_positions"]
    record = make_record(capabilities=shared)
    shared.append("wire_funds")
    assert record.capabilities == ("read_positions",)
    assert isinstance(record.data_classes, tuple)
    with pytest.raises(dataclasses.FrozenInstanceError):
        record.name = "other"  # type: ignore[misc]


def test_a_string_is_not_accepted_as_a_list_of_capabilities(
    make_record: Callable[..., NameRecord],
) -> None:
    with pytest.raises(RecordLoadError, match="sequence of strings"):
        make_record(capabilities="read_positions")


@pytest.mark.parametrize("field", ["capabilities", "data_classes"])
def test_a_string_in_a_file_where_a_list_belongs_is_an_error_not_an_empty_list(field: str) -> None:
    with pytest.raises(RecordLoadError, match=f"'{field}' must be a list of strings"):
        NameRecord.from_dict(raw(**{field: "read_positions"}))


def test_an_unknown_data_class_is_named_in_the_error() -> None:
    with pytest.raises(RecordLoadError, match="top_secret"):
        NameRecord.from_dict(raw(data_classes=["internal", "top_secret"]))


@pytest.mark.parametrize(
    "key",
    [
        "name",
        "kind",
        "version",
        "endpoint",
        "identity",
        "schema_hash",
        "capabilities",
        "data_classes",
        "owner",
    ],
)
def test_every_field_without_a_default_is_required(key: str) -> None:
    data = raw()
    del data[key]
    with pytest.raises(RecordLoadError, match=f"missing required key.*{key}"):
        NameRecord.from_dict(data)


def test_a_misspelled_key_is_rejected_rather_than_ignored() -> None:
    with pytest.raises(RecordLoadError, match=r"unknown key.*data_classs"):
        NameRecord.from_dict(raw(data_classs=["confidential"]))


@pytest.mark.parametrize(
    ("override", "message"),
    [
        ({"kind": "gadget"}, "gadget"),
        ({"status": "retired"}, "retired"),
        ({"version": "v1"}, "Invalid version"),
        ({"ttl_seconds": -1}, "must not be negative"),
        ({"ttl_seconds": "300"}, "integer"),
        ({"ttl_seconds": True}, "integer"),
        ({"identity": "me"}, "'identity' must be a mapping"),
        ({"name": ""}, "must not be empty"),
        ({"endpoint": 5}, "'endpoint' must be a string"),
    ],
)
def test_malformed_fields_are_rejected_with_a_reason(
    override: dict[str, Any], message: str
) -> None:
    with pytest.raises(RecordLoadError, match=message):
        NameRecord.from_dict(raw(**override))


def test_identity_rejects_unknown_keys() -> None:
    with pytest.raises(RecordLoadError, match=r"unknown key.*signed_bye"):
        Identity.from_dict({"public_key_fingerprint": "f", "signed_bye": "x"})


# -- Version ordering ------------------------------------------------------------------------


def test_semver_precedence() -> None:
    ordered = [
        "0.9.9",
        "1.0.0-alpha",
        "1.0.0-alpha.1",
        "1.0.0-alpha.beta",
        "1.0.0-beta",
        "1.0.0-beta.2",
        "1.0.0-beta.11",
        "1.0.0-rc.1",
        "1.0.0",
        "1.0.1",
        "1.10.0",
        "2.0.0",
    ]
    assert sorted(reversed(ordered), key=version_key) == ordered


def test_a_release_candidate_sorts_below_its_release() -> None:
    """Stripping non-digits would turn 1.0.0-rc1 into 1.0.01 and rank it above 1.0.0."""
    assert version_key("1.0.0-rc1") < version_key("1.0.0")


def test_build_metadata_does_not_affect_precedence() -> None:
    assert version_key("1.0.0+build.5") == version_key("1.0.0+other")


@pytest.mark.parametrize("bad", ["1", "1.0", "1.0.0.0", "01.0.0", "1.0.x", "v1.0.0", ""])
def test_a_version_that_is_not_semver_is_rejected(bad: str) -> None:
    with pytest.raises(RecordLoadError, match="Invalid version"):
        version_key(bad)


# -- Agent Cards -----------------------------------------------------------------------------


def identity() -> Identity:
    return Identity(public_key_fingerprint="sha256:" + "33" * 32, signed_by="platform_registry")


def test_importing_an_agent_card_maps_what_the_card_says_and_nothing_else() -> None:
    card = json.loads((FIXTURES / "agent_card.json").read_text())
    record = NameRecord.from_agent_card(
        card, owner="research_team", expires=None, identity=identity(), data_classes=("internal",)
    )
    assert (record.name, record.kind, record.version) == (
        "a2a_market_analyst",
        RecordKind.AGENT,
        "2.0.1",
    )
    assert record.endpoint == "https://agents.a2a.network/market-analyst"
    assert record.capabilities == ("fetch_market_snapshot", "extract_sec_filings")
    assert record.owner == "research_team"
    assert record.signature is None  # the importer never signs


def test_card_skill_ids_are_preferred_over_display_names() -> None:
    card = {
        "name": "a",
        "url": "u",
        "version": "1.0.0",
        "skills": [{"id": "read_positions", "name": "Read Positions"}, {"name": "fallback_name"}],
    }
    record = NameRecord.from_agent_card(
        card, owner="o", expires=None, identity=identity(), data_classes=("public",)
    )
    assert record.capabilities == ("read_positions", "fallback_name")


def test_the_card_hash_changes_when_the_card_changes() -> None:
    kwargs: dict[str, Any] = {
        "owner": "o",
        "expires": None,
        "identity": identity(),
        "data_classes": ("public",),
    }
    card = {"name": "a", "url": "u", "version": "1.0.0", "skills": ["s"]}
    changed = {**card, "description": "now does something else"}
    assert (
        NameRecord.from_agent_card(card, **kwargs).schema_hash
        != NameRecord.from_agent_card(changed, **kwargs).schema_hash
    )


@pytest.mark.parametrize("missing", ["name", "url", "version"])
def test_a_card_missing_a_required_field_is_refused_not_defaulted(missing: str) -> None:
    card = {"name": "a", "url": "u", "version": "1.0.0"}
    del card[missing]
    with pytest.raises(ValueError, match=missing):
        NameRecord.from_agent_card(
            card, owner="o", expires=None, identity=identity(), data_classes=("public",)
        )


def test_the_caller_must_supply_owner_identity_and_data_classes() -> None:
    card = {"name": "a", "url": "u", "version": "1.0.0"}
    with pytest.raises(ValueError, match="owner"):
        NameRecord.from_agent_card(
            card, owner="", expires=None, identity=identity(), data_classes=()
        )
    with pytest.raises(ValueError, match="identity"):
        NameRecord.from_agent_card(
            card,
            owner="o",
            expires=None,
            identity=Identity(public_key_fingerprint=""),
            data_classes=(),
        )
    with pytest.raises(
        TypeError
    ):  # data_classes and expires are required keywords: nothing is guessed
        NameRecord.from_agent_card(card, owner="o", identity=identity())  # type: ignore[call-arg]


def test_a_skill_with_no_name_is_refused() -> None:
    card = {"name": "a", "url": "u", "version": "1.0.0", "skills": [{"description": "?"}]}
    with pytest.raises(ValueError, match="neither 'id' nor 'name'"):
        NameRecord.from_agent_card(
            card, owner="o", expires=None, identity=identity(), data_classes=("public",)
        )


# -- Loading files ---------------------------------------------------------------------------


def test_the_committed_fixture_records_load() -> None:
    (record,) = load_records_file(FIXTURES / "records.yaml")
    assert record.name == "portfolio-data.reader"
    assert record.signature is None


@pytest.mark.parametrize(
    "shape",
    [lambda r: r, lambda r: [r], lambda r: {"records": [r]}],
    ids=["single", "list", "keyed"],
)
def test_a_records_file_may_be_a_single_record_a_list_or_a_records_key(
    tmp_path: Path, shape: Callable[[dict[str, Any]], Any]
) -> None:
    path = tmp_path / "records.yaml"
    path.write_text(json.dumps(shape(raw(name="a.tool"))))  # JSON is valid YAML
    assert [r.name for r in load_records_file(path)] == ["a.tool"]


def test_an_empty_records_file_is_no_records(tmp_path: Path) -> None:
    (tmp_path / "empty.yaml").write_text("")
    assert load_records_file(tmp_path / "empty.yaml") == []


def test_a_bad_record_error_names_the_file_and_the_position(tmp_path: Path) -> None:
    path = tmp_path / "records.yaml"
    path.write_text("- " + "{name: ok, kind: tool}\n")
    with pytest.raises(RecordLoadError) as exc_info:
        load_records_file(path)
    message = str(exc_info.value)
    assert str(path) in message
    assert "record[0]" in message


def test_a_non_mapping_entry_is_an_error_not_skipped(tmp_path: Path) -> None:
    path = tmp_path / "records.yaml"
    path.write_text("- just a string\n")
    with pytest.raises(RecordLoadError, match=r"record\[0\].*expected a mapping"):
        load_records_file(path)


def test_a_missing_or_unparseable_file_is_a_record_load_error(tmp_path: Path) -> None:
    with pytest.raises(RecordLoadError, match="not found"):
        load_records_file(tmp_path / "nope.yaml")
    (tmp_path / "bad.yaml").write_text("a: [unclosed")
    with pytest.raises(RecordLoadError, match="cannot parse"):
        load_records_file(tmp_path / "bad.yaml")


def test_a_records_directory_is_loaded_recursively_in_a_stable_order(tmp_path: Path) -> None:
    def write(path: Path, name: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(raw(name=name)))

    write(tmp_path / "b.json", "b.tool")
    write(tmp_path / "sub" / "a.yaml", "a.tool")
    write(tmp_path / "c.yml", "c.tool")
    names = [r.name for r in load_records_directory(tmp_path)]
    assert names == [r.name for r in load_records_directory(tmp_path)]
    assert sorted(names) == ["a.tool", "b.tool", "c.tool"]
    with pytest.raises(RecordLoadError, match="directory not found"):
        load_records_directory(tmp_path / "missing")
