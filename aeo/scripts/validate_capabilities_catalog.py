#!/usr/bin/env python3
"""Validate docs/capabilities.json against data/capabilities.yml (the source
of truth) and against the real packages/ directory, so the broader catalog
can't silently drop a package the way docs/patterns.json alone never
covered anything outside pyagent-patterns.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    catalog_path = ROOT / "docs" / "capabilities.json"
    source_path = ROOT / "data" / "capabilities.yml"
    packages_dir = ROOT / "packages"

    findings = []

    if not catalog_path.exists():
        print("FAIL: docs/capabilities.json does not exist")
        return 1
    catalog = json.loads(catalog_path.read_text())
    catalog_packages = {p["id"]: p for p in catalog.get("packages", [])}

    # 1. No drift from data/capabilities.yml (the actual source of truth).
    if source_path.exists():
        source = yaml.safe_load(source_path.read_text())
        source_ids = {p["id"] for p in source["packages"]}
        catalog_ids = set(catalog_packages)
        status = "PASS" if source_ids == catalog_ids else "FAIL"
        findings.append(
            {
                "check": "no_drift_from_source",
                "status": status,
                "detail": {
                    "only_in_source": sorted(source_ids - catalog_ids),
                    "only_in_catalog": sorted(catalog_ids - source_ids),
                },
            }
        )
    else:
        findings.append(
            {
                "check": "no_drift_from_source",
                "status": "FAIL",
                "detail": "data/capabilities.yml missing",
            }
        )

    # 2. Every real package under packages/ that publishes to PyPI (has its
    #    own pyproject.toml) is represented in the catalog — the whole point
    #    of this file is breadth, so a missing package is a regression.
    real_package_dirs = sorted(
        p.name for p in packages_dir.iterdir() if p.is_dir() and (p / "pyproject.toml").exists()
    )
    missing = [name for name in real_package_dirs if name not in catalog_packages]
    status = "PASS" if not missing else "FAIL"
    findings.append(
        {
            "check": "every_real_package_covered",
            "status": status,
            "detail": missing or f"all {len(real_package_dirs)} packages under packages/ are covered",
        }
    )

    # 3. Every package entry has at minimum id/pypi/install/description/docs.
    required_fields = ["id", "pypi", "install", "description", "docs"]
    missing_fields_by_package = {}
    for pkg_id, pkg in catalog_packages.items():
        missing_f = [f for f in required_fields if f not in pkg]
        if missing_f:
            missing_fields_by_package[pkg_id] = missing_f
    status = "PASS" if not missing_fields_by_package else "FAIL"
    findings.append(
        {
            "check": "required_fields_present",
            "status": status,
            "detail": missing_fields_by_package or "all packages have all required fields",
        }
    )

    for f in findings:
        marker = "OK" if f["status"] == "PASS" else "FAIL"
        print(f"[{marker}] {f['check']}: {f['detail']}")

    out = ROOT / "aeo" / "baselines" / "capabilities-catalog-validation.json"
    out.write_text(json.dumps(findings, indent=2), encoding="utf-8")
    print(f"\nWrote {out}")
    return 0 if all(f["status"] == "PASS" for f in findings) else 1


if __name__ == "__main__":
    sys.exit(main())
