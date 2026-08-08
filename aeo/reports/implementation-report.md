# White-Box Implementation Conformance Report

**Audited against:** `aeo/requirements.yaml`
**Target:** `http://localhost:8002` (local build; production `pyagent.org` audit pending push — see note below)
**Method:** deterministic scripts reading raw HTTP responses, never a rendered browser DOM — `aeo/scripts/crawl.py`, `validate_jsonld.py`, `validate_catalog.py`, `validate_html.py`.

## Summary

| Area | Status | Evidence |
|---|---|---|
| Crawlability — page availability | PASS | 8/8 key URLs return 200 |
| Crawlability — static content visibility | PASS | 18/18 pattern names present in raw HTML, no JS required |
| Crawlability — user-agent blocking | PASS | 5/5 crawler UAs (OAI-SearchBot, Googlebot, bingbot, ClaudeBot, PerplexityBot) return 200 |
| Crawlability — robots.txt / sitemap.xml | PASS | Both exist; robots.txt explicitly allows AI crawlers |
| JSON-LD — homepage SoftwareApplication | PASS | Valid, parses |
| JSON-LD — deep-page BreadcrumbList | PASS | Valid, parses, breadcrumb chain matches page H1 on both tested pages |
| Machine-readable catalog — schema | PASS | `docs/patterns.json`: 18/18 patterns, all required fields present |
| Machine-readable catalog — no drift | PASS | `docs/patterns.json` matches `data/patterns.yml` exactly, no dangling `pairs_with` refs |
| Entity — canonical repo identity | PASS | `github.com/pyagent-core/pyagent` present on homepage |
| Entity — four-pillar labels | PASS | Manifest, Execution & Routing, Context & Memory, Observability all present |
| Regression — fabricated commands | PASS | Neither `pyagent-blueprint simulate` nor the fabricated `--adapter` flag reappear anywhere in crawled HTML |

**0 critical failures. 0 non-critical failures.** Every check that was run, passed.

## What this report does NOT cover (honest gaps)

- **Production `pyagent.org` audit is stale.** `curl https://pyagent.org/patterns.json` returns 404 as of this audit — this session's work (positioning fix, `patterns.json`, spec-driven framing, Portfolio Review reference architecture) is committed to the working tree but not yet pushed. The checks above ran against the local build, which contains the same code. Re-run `crawl.py --base-url https://pyagent.org` after push to confirm production parity.
- **Only 2 pages checked for JSON-LD**, not every page on the site. `/packages/patterns/` and the Portfolio Review recipe were chosen as representative deep pages; a full-site crawl would give more confidence but wasn't run this pass.
- **No `SoftwareSourceCode`/`Organization`/`TechArticle`/`DefinedTerm` schema types exist** — the original AEO proposal wanted these; they weren't built (evaluated as scope not yet justified) and are absent from `aeo/requirements.yaml`'s `machine_readable.required` list accordingly. This isn't a failure against the contract — the contract doesn't require them.
- **No CDN/WAF-level check** — GitHub Pages hosting has no WAF layer to test; this would matter if PyAgent ever moves to CDN-fronted hosting with IP-based rules, which the original proposal specifically warned can't be verified by user-agent spoofing alone.
