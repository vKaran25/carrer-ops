# Job discovery `[P1/P2 foundations / P4 readiness]`

## Core retrieval

- FR-SCOUT-1: Preserve `search_jobs(query_spec: dict, limit: int = 10) -> list[dict]`; return source-backed title/company/location/URL/description evidence. The orchestrator also reports checked coverage and failures.
- FR-SCOUT-2: Prefer accessible public ATS JSON (existing Greenhouse/Lever/Workday paths), then permitted static/rendered retrieval within resource/access budgets. Existing adapters are not a guarantee of every employer or platform.
- FR-SCOUT-3: Deduplicate canonical jobs and active tracker URLs within the authenticated account. Distinguish different requisitions and preserve attribution.
- Filter before result/candidate caps; interleave eligible sources; report retrieval, filter/tracker exclusion and failure counts. Initial configured employers are seeds, never the definition of Indian coverage.

## Approved discovery direction

- Tavily basic search plus configured and dynamically discovered accessible employer sources. No JSearch implementation is approved. Keys stay server-side.
- Current prototype defaults: up to 3 basic queries and 8 discovered employer pages, with a 10-minute repeat-query cache. P4 multi-user/provider budgets and concurrency values need measurement and user discussion; do not treat prototype defaults as verified beta capacity.
- Prepare short role/skill/location/company queries from explicit instructions or stored skills. Never send full resumes or identity facts to Tavily.
- Require retrieved usable JD evidence for scoring; source snippets/inaccessible leads stay separate and unscored. Preserve known publication/expiry and retrieval times; unknown dates do not satisfy a mandatory recency filter.
- Seek employer copies for indexed LinkedIn leads within the same budget. No LinkedIn fetch/login/scraping. Do not imply that Tavily grants access to all LinkedIn descriptions.
- Missing/invalid keys, malformed responses, source failures and quotas must be visible; eligible partial results may survive. Poor Indian coverage blocks beta pending a user-reviewed remedy.
- General location handling must support Indian and international cities/nearby regions without a Delhi-only solution. Agree the location-resolution approach with the user; unknown locations never meet mandatory filters.

## Acceptance

Keep existing isolated source/auth/quota/no-key/expiry/deduplication/cap/no-LinkedIn-fetch checks. Add an independently reviewed live benchmark for Indian cities and levels, independently evidenced smaller/non-seed employers and international cases. Record actual relevant/eligible jobs recovered and missed, description completeness, duplicates, link validity, known freshness and credits.

Agree numerical pass thresholds before running the release evaluation. Zero mandatory-filter violations or fabricated evidence; no nonempty-result guarantee when no eligible opening exists. A missing key or weak source coverage is pending/failed acceptance, never a synthetic fallback. Coverage review and real source/model evidence precede beta. See `core-release.md` and `../tasks/phase-4-tasks.md`.
