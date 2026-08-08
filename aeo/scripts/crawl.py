#!/usr/bin/env python3
"""Fetch pyagent.org (or a local build) with multiple user agents and cache
raw HTML for downstream validators.

This exists specifically to catch the failure mode named in the AEO
proposal: "visual browser shows 18 patterns, crawler HTML shows 0" — i.e.
content that only renders via client-side JS. Every check here reads the
RAW response body, never a browser-rendered DOM.

Usage:
    python aeo/scripts/crawl.py --base-url https://pyagent.org
    python aeo/scripts/crawl.py --base-url http://localhost:8002
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path

CACHE_DIR = Path(__file__).resolve().parents[1] / "baselines" / "crawl-cache"

PAGES = [
    "/",
    "/patterns.json",
    "/robots.txt",
    "/sitemap.xml",
    "/llms.txt",
    "/packages/patterns/",
    "/cookbook/",
    "/cookbook/finance-trading/portfolio-review/",
]

USER_AGENTS = [
    "OAI-SearchBot",
    "Googlebot",
    "bingbot",
    "ClaudeBot",
    "PerplexityBot",
]

# Content markers that must survive to raw HTML — no JS required to see them.
PATTERN_NAMES = [
    "Supervisor", "Pipeline", "Fan-Out", "Hierarchical", "Orchestrator-Workers",
    "Self-Reflection", "Cross-Reflection", "Debate", "Voting", "Evaluator-Optimizer",
    "Role-Based", "Layered", "Topology", "Blackboard", "ReAct", "Talker-Reasoner",
    "Swarm", "Human-in-the-Loop",
]


def fetch(url: str, user_agent: str) -> tuple[int, str]:
    req = urllib.request.Request(url, headers={"User-Agent": user_agent})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return exc.code, ""
    except Exception as exc:  # noqa: BLE001
        return 0, str(exc)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="https://pyagent.org")
    args = parser.parse_args()
    base = args.base_url.rstrip("/")

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    results: dict = {"base_url": base, "pages": {}, "user_agent_check": {}}

    print(f"Crawling {base} ...")
    for page in PAGES:
        status, body = fetch(base + page, "Mozilla/5.0 (aeo-crawl-check)")
        cache_path = CACHE_DIR / (page.strip("/").replace("/", "_") or "index")
        cache_path = cache_path.with_suffix(".html" if not page.endswith(".json") else ".json")
        if body:
            cache_path.write_text(body, encoding="utf-8")
        results["pages"][page] = {
            "status": status,
            "bytes": len(body),
            "cached_to": str(cache_path.relative_to(CACHE_DIR.parents[1])) if body else None,
        }
        marker = "OK" if status == 200 else "FAIL"
        print(f"  [{marker}] {page} -> {status} ({len(body)} bytes)")

    # Pattern-name visibility check against raw HTML (the specific failure
    # mode this script exists to catch).
    _, patterns_html = fetch(base + "/packages/patterns/", "Mozilla/5.0 (aeo-crawl-check)")
    found = [p for p in PATTERN_NAMES if p.split()[0] in patterns_html or p in patterns_html]
    results["static_content_check"] = {
        "expected_patterns": len(PATTERN_NAMES),
        "found_in_raw_html": len(found),
        "missing": [p for p in PATTERN_NAMES if p not in found],
    }
    print(
        f"  Pattern names visible in raw HTML: {len(found)}/{len(PATTERN_NAMES)}"
    )

    # User-agent blocking check.
    print("Checking for user-agent-based blocking...")
    for ua in USER_AGENTS:
        status, _ = fetch(base + "/", ua)
        results["user_agent_check"][ua] = status
        print(f"  {ua}: {status}")

    out_path = CACHE_DIR.parent / "crawl-results.json"
    out_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nWrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
