"""Tests for loading an ``x-pyagent:dns`` block from a blueprint file.

The end-to-end tests build a real project in ``tmp_path`` with a signed record and a generated
trusted key, load it the way a user would, and then ask the middleware for decisions. The
committed fixtures hold only a public key, so they can show the wiring but not a verified call.
"""

from __future__ import annotations

import os
import subprocess
import sys
import warnings
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
import yaml
from pyagent_dns.authority import Action, GrantLoadError
from pyagent_dns.blueprint import (
    EXTENSION_KEY,
    DnsBlueprintError,
    DnsEnforcement,
    adapter_diagnostics,
    load_blueprint_dns,
    load_dns_block,
)
from pyagent_dns.diagnostics import AUTHORITY_UNSUPPORTED, DNS_UNSUPPORTED
from pyagent_dns.middleware import DnsMiddleware
from pyagent_dns.signing import VerificationStatus

if TYPE_CHECKING:
    from collections.abc import Callable

    from pyagent_dns.records import NameRecord

FIXTURES = Path(__file__).parent / "fixtures"
PURPOSE = "portfolio_review"

BLUEPRINT: dict[str, Any] = {
    "api_version": "pyagent/v1",
    "metadata": {"name": "demo", "version": "1.0.0", "owner": "team"},
    "providers": {"primary": {"provider": "mock", "model": "mock-llm"}},
    "agents": {"research_agent": {"prompt": "You research.", "provider": "primary"}},
    "workflows": {
        "main": {
            "pattern": "sequential_chain",
            "agents": {"stages": {"research": "research_agent"}},
        }
    },
}

GRANT: dict[str, Any] = {
    "grant_id": "g1",
    "principal": "research_agent",
    "action": "call",
    "capability": "portfolio-data.reader",
    "purpose": PURPOSE,
    "resource": {"data_classes": ["internal"]},
}


def write_yaml(path: Path, data: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path


@pytest.fixture
def project(
    tmp_path: Path,
    make_record: Callable[..., NameRecord],
    signer_name: str,
    public_key_pem: str,
    public_key_fingerprint: str,
) -> Callable[..., Path]:
    """Write a blueprint plus the files it points at, and return the blueprint's path.

    Every default is a working configuration; a test overrides only what it is about.
    """

    def build(
        *,
        record: NameRecord | None = None,
        grants: Any = None,
        trusted: bool = True,
        block: dict[str, Any] | None = None,
        directory: str = "",
    ) -> Path:
        root = tmp_path / directory
        write_yaml(root / "records.yaml", [(record or make_record()).to_dict()])
        write_yaml(root / "grants.yaml", [GRANT] if grants is None else grants)
        write_yaml(
            root / "trusted_keys.yaml",
            {
                "keys": [
                    {
                        "signer": signer_name,
                        "public_key_fingerprint": public_key_fingerprint,
                        "public_key": public_key_pem,
                    }
                ]
            },
        )
        default_block: dict[str, Any] = {
            "records_files": ["records.yaml"],
            "grants_files": ["grants.yaml"],
            "enforcement": "required",
        }
        if trusted:
            default_block["trusted_keys_file"] = "trusted_keys.yaml"
        return write_yaml(
            root / "blueprint.yaml", BLUEPRINT | {EXTENSION_KEY: block or default_block}
        )

    return build


def call_portfolio_reader(path: Path) -> str:
    bundle = load_blueprint_dns(path)
    assert bundle is not None
    middleware = DnsMiddleware(bundle.resolver, bundle.graph)
    tools = middleware.guard_tools(
        {"portfolio-data.reader": lambda _: "positions"},
        principal_chain=["research_agent"],
        purpose=PURPOSE,
    )
    return tools["portfolio-data.reader"]("x")


# -- Loading a working project ---------------------------------------------------------------


def test_a_signed_record_and_a_matching_grant_allow_the_call_end_to_end(
    project: Callable[..., Path],
) -> None:
    assert call_portfolio_reader(project()) == "positions"


def test_the_bundle_wires_registry_resolver_and_graph_together(
    project: Callable[..., Path],
) -> None:
    path = project()
    bundle = load_blueprint_dns(path)
    assert bundle is not None
    assert bundle.source_path == path
    assert bundle.spec.enforcement is DnsEnforcement.REQUIRED
    assert "portfolio-data.reader" in bundle.registry
    (grant,) = bundle.graph.grants_for("research_agent")
    assert (grant.grant_id, grant.action) == ("g1", Action.CALL)
    resolution = bundle.resolver.resolve("portfolio-data.reader")
    assert resolution is not None
    assert resolution.verification == VerificationStatus.VERIFIED


def test_a_tampered_record_is_denied_even_though_a_grant_names_it(
    project: Callable[..., Path], make_record: Callable[..., NameRecord]
) -> None:
    out = call_portfolio_reader(project(record=make_record(tamper=True)))
    assert out.startswith("DENIED [RECORD_SIGNATURE_INVALID]")


def test_an_unsigned_record_is_denied_as_unverified(
    project: Callable[..., Path], make_record: Callable[..., NameRecord]
) -> None:
    out = call_portfolio_reader(project(record=make_record(sign=False)))
    assert out.startswith("DENIED [RECORD_UNVERIFIED]")


def test_with_no_trusted_keys_file_nothing_can_be_verified_so_nothing_is_allowed(
    project: Callable[..., Path],
) -> None:
    out = call_portfolio_reader(project(trusted=False))
    assert out.startswith("DENIED [RECORD_UNVERIFIED]")


def test_a_blueprint_with_no_grants_loads_and_denies_everything(
    project: Callable[..., Path],
) -> None:
    assert call_portfolio_reader(project(grants=[])).startswith("DENIED [NO_GRANT]")


def test_relative_paths_resolve_against_the_blueprint_not_the_working_directory(
    project: Callable[..., Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = project(directory="nested/project")
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    assert call_portfolio_reader(path) == "positions"


def test_the_committed_fixture_blueprint_loads_and_cannot_verify_its_unsignable_record() -> None:
    """Its key has no private half, so the record is unverified and the middleware refuses it."""
    bundle = load_blueprint_dns(FIXTURES / "blueprint_with_dns.yaml")
    assert bundle is not None
    assert [g.grant_id for g in bundle.graph.grants_for("research_agent")] == ["grant_fixture_001"]
    resolution = bundle.resolver.resolve("portfolio-data.reader")
    assert resolution is not None
    assert resolution.verification != VerificationStatus.VERIFIED


# -- A blueprint without a dns block ---------------------------------------------------------


def test_a_blueprint_without_the_block_loads_as_none() -> None:
    assert load_blueprint_dns(FIXTURES / "blueprint_without_dns.yaml") is None


def test_an_absent_key_is_none_but_a_present_empty_one_is_an_error() -> None:
    assert load_dns_block({"agents": {}}) is None
    with pytest.raises(DnsBlueprintError, match="must be a mapping, got NoneType"):
        load_dns_block({EXTENSION_KEY: None})


def test_an_empty_mapping_is_a_valid_block_with_closed_defaults(tmp_path: Path) -> None:
    path = write_yaml(tmp_path / "bp.yaml", BLUEPRINT | {EXTENSION_KEY: {}})
    bundle = load_blueprint_dns(path)
    assert bundle is not None
    assert bundle.spec.enforcement is DnsEnforcement.REQUIRED
    assert len(bundle.registry) == 0


# -- Malformed blocks and files fail loudly, naming the blueprint ----------------------------


@pytest.mark.parametrize(
    ("block", "message"),
    [
        ("a string", "must be a mapping, got str"),
        (["records.yaml"], "must be a mapping, got list"),
        ({"records_file": ["r.yaml"]}, "records_file"),  # a typo must not be ignored
        ({"enforcement": "optional"}, "enforcement"),
        ({"records_files": "records.yaml"}, "records_files"),
        ({"trusted_keys_file": ["a", "b"]}, "trusted_keys_file"),
    ],
)
def test_a_malformed_block_is_rejected_and_the_error_names_the_blueprint(
    tmp_path: Path, block: Any, message: str
) -> None:
    path = write_yaml(tmp_path / "bp.yaml", BLUEPRINT | {EXTENSION_KEY: block})
    with pytest.raises(DnsBlueprintError, match=message) as exc_info:
        load_blueprint_dns(path)
    assert str(path) in str(exc_info.value)


def test_a_missing_referenced_file_is_named_with_its_role_and_resolved_path(
    project: Callable[..., Path],
) -> None:
    path = project(
        block={"records_files": ["records.yaml", "nope.yaml"], "grants_files": ["grants.yaml"]}
    )
    with pytest.raises(DnsBlueprintError) as exc_info:
        load_blueprint_dns(path)
    message = str(exc_info.value)
    assert str(path) in message
    assert "records_files[1]" in message
    assert str(path.parent / "nope.yaml") in message


@pytest.mark.parametrize(
    ("block_key", "write_bad", "message"),
    [
        ("records_files", [{"name": "x"}], r"record\[0\].*missing required key.*capabilities"),
        ("grants_files", [{**GRANT, "efect": "allow"}], "efect"),
        (
            "trusted_keys_file",
            {"keys": [{"signer": "s"}]},
            r"keys\[0\].*missing required key.*public_key",
        ),
    ],
)
def test_a_bad_referenced_file_surfaces_its_own_error_through_the_blueprint(
    project: Callable[..., Path], block_key: str, write_bad: Any, message: str
) -> None:
    path = project()
    block = yaml.safe_load(path.read_text())[EXTENSION_KEY]
    bad = write_yaml(path.parent / "bad.yaml", write_bad)
    block[block_key] = bad.name if block_key == "trusted_keys_file" else [bad.name]
    write_yaml(path, BLUEPRINT | {EXTENSION_KEY: block})
    with pytest.raises(DnsBlueprintError, match=message) as exc_info:
        load_blueprint_dns(path)
    assert str(path) in str(exc_info.value)


def test_a_grants_file_that_widens_a_delegation_is_rejected_at_load(
    project: Callable[..., Path],
) -> None:
    """Attenuation is enforced when the graph is built, so a bad file cannot yield a live grant."""
    parent = {**GRANT, "delegation": {"allowed": True}, "limits": {"max_records_per_call": 10}}
    child = {
        **GRANT,
        "grant_id": "g2",
        "principal": "worker",
        "parent_grant_id": "g1",
        "limits": {"max_records_per_call": 1000},
    }
    with pytest.raises(DnsBlueprintError, match="max_records_per_call"):
        load_blueprint_dns(project(grants=[parent, child]))


def test_a_blueprint_that_does_not_exist_raises_file_not_found(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match=r"missing\.yaml"):
        load_blueprint_dns(tmp_path / "missing.yaml")


@pytest.mark.parametrize(
    ("text", "message"), [("- a\n- b\n", "must be a mapping"), ("a: [unclosed", "cannot parse")]
)
def test_a_blueprint_that_is_not_a_yaml_mapping_is_a_load_error(
    tmp_path: Path, text: str, message: str
) -> None:
    path = tmp_path / "bp.yaml"
    path.write_text(text)
    with pytest.raises(DnsBlueprintError, match=message):
        load_blueprint_dns(path)


# -- Advisory enforcement --------------------------------------------------------------------


def test_advisory_turns_a_broken_referenced_file_into_a_warning_and_no_bundle(
    project: Callable[..., Path],
) -> None:
    path = project(
        block={"grants_files": ["gone.yaml"], "enforcement": "advisory"},
    )
    with pytest.warns(UserWarning, match=r"advisory.*no dns bundle"):
        assert load_blueprint_dns(path) is None


def test_advisory_does_not_warn_when_everything_loads(project: Callable[..., Path]) -> None:
    path = project()
    block = yaml.safe_load(path.read_text())[EXTENSION_KEY] | {"enforcement": "advisory"}
    write_yaml(path, BLUEPRINT | {EXTENSION_KEY: block})
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        assert load_blueprint_dns(path) is not None


def test_a_block_that_cannot_even_be_parsed_raises_whatever_it_says_about_enforcement(
    tmp_path: Path,
) -> None:
    """Its own `advisory` cannot be believed when the rest of the block is malformed."""
    path = write_yaml(
        tmp_path / "bp.yaml", BLUEPRINT | {EXTENSION_KEY: {"enforcement": "advisory", "typo": 1}}
    )
    with pytest.raises(DnsBlueprintError, match="typo"):
        load_blueprint_dns(path)


def test_grant_load_errors_are_wrapped_not_leaked_as_bare_value_errors(
    project: Callable[..., Path],
) -> None:
    with pytest.raises(DnsBlueprintError) as exc_info:
        load_blueprint_dns(project(grants=[{**GRANT, "action": "teleport"}]))
    assert isinstance(exc_info.value.__cause__, GrantLoadError)


# -- Adapter diagnostics ---------------------------------------------------------------------


@pytest.mark.parametrize(
    ("present", "capabilities", "expected"),
    [
        (True, set(), [DNS_UNSUPPORTED, AUTHORITY_UNSUPPORTED]),
        (True, {"routing"}, [DNS_UNSUPPORTED, AUTHORITY_UNSUPPORTED]),
        (True, {"dns"}, []),
        (False, set(), []),
    ],
)
def test_adapter_diagnostics(present: bool, capabilities: set[str], expected: list[str]) -> None:
    assert adapter_diagnostics(present, adapter_capabilities=capabilities) == expected


# -- Relationship to pyagent-blueprint -------------------------------------------------------


def test_the_extension_key_matches_the_one_pyagent_blueprint_would_build() -> None:
    extensions = pytest.importorskip("pyagent_blueprint.extensions")
    assert extensions.namespaced_key("dns") == EXTENSION_KEY


def test_known_limitation_pyagent_blueprint_drops_the_block_but_this_loader_still_finds_it() -> (
    None
):
    """Documented in blueprint.py: the block survives on disk, not through blueprint's own load.

    If this test starts failing because the blueprint now keeps the block, the limitation is
    fixed upstream and the module docstring should say so.
    """
    loader = pytest.importorskip("pyagent_blueprint.loader")
    path = FIXTURES / "blueprint_with_dns.yaml"
    spec = loader.load_blueprint(path)
    assert EXTENSION_KEY not in spec.model_dump()
    assert load_blueprint_dns(path) is not None


# -- Importing the package ---------------------------------------------------------------------


def test_importing_pyagent_dns_does_not_import_the_optional_packages() -> None:
    optional = ["pyagent_trace", "pyagent_context", "pyagent_blueprint", "pyagent_router"]
    code = (
        "import sys\n"
        "import pyagent_dns, pyagent_dns.blueprint, pyagent_dns.diagnostics, "
        "pyagent_dns.events, pyagent_dns.middleware\n"
        f"loaded = [m for m in {optional!r} if m in sys.modules]\n"
        "print('LOADED:' + ','.join(loaded))\n"
    )
    src = Path(__file__).parent.parent / "src"
    env = {
        **os.environ,
        "PYTHONPATH": os.pathsep.join([str(src), os.environ.get("PYTHONPATH", "")]),
    }
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, env=env, check=False
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "LOADED:"
