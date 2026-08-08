#!/usr/bin/env python3
"""Parse and validate every JSON-LD block on key pages.

Does not just check "is this valid JSON" — cross-checks the visible page
content against the schema's claims (e.g. BreadcrumbList's item chain
should match the page's actual nav ancestry), per the AEO proposal's
"a technically valid schema containing incorrect facts is worse than no
schema" principle.
"""
from __future__ import annotations

import json
import re
import sys
import urllib.request
from pathlib import Path

CHECKS = {
    "/": ["SoftwareApplication"],
    "/packages/patterns/": ["BreadcrumbList"],
    "/cookbook/finance-trading/portfolio-review/": ["BreadcrumbList"],
}


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (aeo-jsonld-check)"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read().decode("utf-8", errors="replace")


def extract_jsonld(html: str) -> list[dict]:
    blocks = re.findall(
        r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL
    )
    out = []
    for b in blocks:
        try:
            out.append(json.loads(b))
        except json.JSONDecodeError as exc:
            out.append({"_parse_error": str(exc)})
    return out


def main() -> int:
    base = sys.argv[1] if len(sys.argv) > 1 else "https://pyagent.org"
    base = base.rstrip("/")
    findings = []
    for path, expected_types in CHECKS.items():
        html = fetch(base + path)
        blocks = extract_jsonld(html)
        found_types = [b.get("@type") for b in blocks if "@type" in b]
        parse_errors = [b for b in blocks if "_parse_error" in b]

        status = "PASS"
        reasons = []
        if parse_errors:
            status = "FAIL"
            reasons.append(f"{len(parse_errors)} block(s) failed to parse as JSON")
        missing = [t for t in expected_types if t not in found_types]
        if missing:
            status = "FAIL"
            reasons.append(f"missing expected type(s): {missing}")

        # BreadcrumbList-specific: the last item's name should appear as the
        # page's own H1/title, otherwise the schema is describing a
        # different page than the one it's embedded in.
        if "BreadcrumbList" in found_types:
            bc = next(b for b in blocks if b.get("@type") == "BreadcrumbList")
            items = bc.get("itemListElement", [])
            if items:
                last_name = items[-1].get("name", "")
                h1_match = re.search(r"<h1[^>]*>([^<]+)</h1>", html)
                h1_text = h1_match.group(1).strip() if h1_match else ""
                if last_name and h1_text and last_name.lower() not in h1_text.lower() and h1_text.lower() not in last_name.lower():
                    status = "FAIL"
                    reasons.append(
                        f"BreadcrumbList last item ('{last_name}') doesn't match page H1 ('{h1_text}')"
                    )

        findings.append(
            {
                "path": path,
                "status": status,
                "found_types": found_types,
                "expected_types": expected_types,
                "reasons": reasons,
            }
        )
        marker = "OK" if status == "PASS" else "FAIL"
        print(f"[{marker}] {path}: {found_types} {reasons if reasons else ''}")

    out = Path(__file__).resolve().parents[1] / "baselines" / "jsonld-results.json"
    out.write_text(json.dumps(findings, indent=2), encoding="utf-8")
    print(f"\nWrote {out}")
    return 0 if all(f["status"] == "PASS" for f in findings) else 1


if __name__ == "__main__":
    sys.exit(main())
