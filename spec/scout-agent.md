# Scout Agent (Job Discovery)

## Requirements
- FR-SCOUT-1 `[P1]`: Tool contract: `search_jobs(query_spec: dict, limit: int = 10) -> list[dict]`. Each result dict: `title, company, location, url, description_snippet`.
- FR-SCOUT-2 `[P2]`: Before BS4, check a `known_ats` lookup table; if the company matches Greenhouse/Lever/Workday, call their public JSON API directly. Fall back to BS4 for static pages. Fall back further to Playwright for JS-heavy sites with no API.
- FR-SCOUT-3 `[P1]`: Deduplicate against jobs already in the user's tracker.

## P1 scope note
For P1, implement the BS4 path only, reusing the builder's existing BS4 crawler (crawl/queue/dedupe logic reused, extraction logic rewritten for job postings). The ATS-lookup and Playwright paths are `[P2]` — do not build them yet, but keep `search_jobs`'s signature stable so P2 can add the ATS check *inside* the function without changing its contract.

## Acceptance
Three varied natural-language queries each return correctly-parsed, capped results. (ATS-path acceptance — a known Greenhouse-hosted company resolves via JSON API, not BS4 — applies at P2, not now.)

## Data model touched
`JobPosting` — see `data-models.md`.
