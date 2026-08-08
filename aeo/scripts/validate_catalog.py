#!/usr/bin/env python3
"""Validate docs/patterns.json against aeo/requirements.yaml's declared
schema, and cross-check it hasn't drifted from data/patterns.yml (the
source of truth) or from the actual pattern .md pages.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    req = yaml.safe_load((ROOT / "aeo" / "requirements.yaml").read_text())
    required_fields = req["pattern_metadata"]["required_fields"]
    expected_count = req["pattern_metadata"]["pattern_count"]

    catalog_path = ROOT / "docs" / "patterns.json"
    source_path = ROOT / "data" / "patterns.yml"

    findings = []

    if not catalog_path.exists():
        print("FAIL: docs/patterns.json does not exist")
        return 1
    catalog = json.loads(catalog_path.read_text())
    patterns = catalog.get("patterns", [])

    # 1. Field completeness.
    missing_fields_by_pattern = {}
    for p in patterns:
        missing = [f for f in required_fields if f not in p]
        if missing:
            missing_fields_by_pattern[p.get("id", "?")] = missing
    status = "PASS" if not missing_fields_by_pattern else "FAIL"
    findings.append(
        {
            "check": "required_fields_present",
            "status": status,
            "detail": missing_fields_by_pattern or "all patterns have all required fields",
        }
    )

    # 2. Count matches declared expectation.
    status = "PASS" if len(patterns) == expected_count else "FAIL"
    findings.append(
        {
            "check": "pattern_count",
            "status": status,
            "detail": f"expected {expected_count}, found {len(patterns)}",
        }
    )

    # 3. No drift from data/patterns.yml (the actual source of truth).
    if source_path.exists():
        source = yaml.safe_load(source_path.read_text())
        source_ids = {p["id"] for p in source["patterns"]}
        catalog_ids = {p["id"] for p in patterns}
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
            {"check": "no_drift_from_source", "status": "FAIL", "detail": "data/patterns.yml missing"}
        )

    # 4. pairs_with references only exist as real pattern IDs (no dangling refs).
    catalog_ids = {p["id"] for p in patterns}
    dangling = []
    for p in patterns:
        for pw in p.get("pairs_with", []):
            if pw["pattern"] not in catalog_ids:
                dangling.append((p["id"], pw["pattern"]))
    status = "PASS" if not dangling else "FAIL"
    findings.append({"check": "no_dangling_pairs_with_refs", "status": status, "detail": dangling})

    for f in findings:
        marker = "OK" if f["status"] == "PASS" else "FAIL"
        print(f"[{marker}] {f['check']}: {f['detail']}")

    out = ROOT / "aeo" / "baselines" / "catalog-validation.json"
    out.write_text(json.dumps(findings, indent=2), encoding="utf-8")
    print(f"\nWrote {out}")
    return 0 if all(f["status"] == "PASS" for f in findings) else 1


if __name__ == "__main__":
    sys.exit(main())
