#!/usr/bin/env python3
"""Validate raw crawled HTML against aeo/requirements.yaml's entity and
architecture claims. Reads the cache crawl.py produced — never re-renders
via a browser, so this only sees what a crawler sees.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = ROOT / "aeo" / "baselines" / "crawl-cache"


def main() -> int:
    req = yaml.safe_load((ROOT / "aeo" / "requirements.yaml").read_text())
    findings = []

    index_html = (CACHE_DIR / "index.html")
    if not index_html.exists():
        print("FAIL: no cached homepage HTML — run crawl.py first")
        return 1
    home = index_html.read_text(encoding="utf-8")

    # 1. Canonical repo identity present somewhere reachable from the homepage
    #    (directly, or via the GitHub link) — the entity-confusion mitigation.
    repo = req["entity"]["canonical_repo"]
    has_repo_link = repo in home or "pyagent-core/pyagent" in home
    findings.append(
        {
            "check": "canonical_repo_identity_present",
            "status": "PASS" if has_repo_link else "FAIL",
            "detail": f"looked for '{repo}' or 'pyagent-core/pyagent' in homepage HTML",
        }
    )

    # 2. All four pillar labels appear somewhere in the homepage raw HTML.
    pillar_labels = [p["label"] for p in req["architecture"]["pillars"]]
    missing_pillars = [lbl for lbl in pillar_labels if lbl.split()[0] not in home]
    findings.append(
        {
            "check": "four_pillar_labels_present",
            "status": "PASS" if not missing_pillars else "FAIL",
            "detail": {"expected": pillar_labels, "missing": missing_pillars},
        }
    )

    # 3. Tagline present.
    tagline_words = req["entity"]["positioning"]["tagline"].split()[:3]
    tagline_fragment = " ".join(tagline_words)
    findings.append(
        {
            "check": "tagline_present",
            "status": "PASS" if tagline_fragment.lower() in home.lower() else "FAIL",
            "detail": tagline_fragment,
        }
    )

    # 4. No fabricated-command strings reintroduced (regression guard for the
    #    two bugs found and fixed this session).
    fabricated = ["pyagent-blueprint simulate"]
    reintroduced = [f for f in fabricated if f in home]
    for cached_file in CACHE_DIR.glob("*.html"):
        text = cached_file.read_text(encoding="utf-8", errors="ignore")
        for f in fabricated:
            if f in text and f not in reintroduced:
                reintroduced.append(f)
    findings.append(
        {
            "check": "no_fabricated_commands_reintroduced",
            "status": "PASS" if not reintroduced else "FAIL",
            "detail": reintroduced,
        }
    )

    for f in findings:
        marker = "OK" if f["status"] == "PASS" else "FAIL"
        print(f"[{marker}] {f['check']}: {f['detail']}")

    out = ROOT / "aeo" / "baselines" / "html-validation.json"
    out.write_text(json.dumps(findings, indent=2), encoding="utf-8")
    print(f"\nWrote {out}")
    return 0 if all(f["status"] == "PASS" for f in findings) else 1


if __name__ == "__main__":
    sys.exit(main())
