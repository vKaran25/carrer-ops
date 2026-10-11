# Scout Agent (Job Discovery)

## Requirements
- FR-SCOUT-1 `[P1]`: Tool contract: `search_jobs(query_spec: dict, limit: int = 10) -> list[dict]`. Each result dict: `title, company, location, url, description_snippet`.
- FR-SCOUT-2 `[P2]`: Before BS4, check a `known_ats` lookup table; if the company matches Greenhouse/Lever/Workday, call their public JSON API directly. Fall back to BS4 for static pages. Fall back further to Playwright for JS-heavy sites with no API.
- FR-SCOUT-3 `[P1]`: Deduplicate against jobs already in the user's tracker.

## P1 scope note
For P1, implement the BS4 path only, reusing the builder's existing BS4 crawler (crawl/queue/dedupe logic reused, extraction logic rewritten for job postings). The ATS-lookup and Playwright paths are `[P2]` — do not build them yet, but keep `search_jobs`'s signature stable so P2 can add the ATS check *inside* the function without changing its contract.

- Apply mandatory query filters across retrieved postings before the result/candidate cap. Interleave matching sources so a large first company cannot hide later sources. Persist retrieval, tracker-exclusion and filter-exclusion counts to explain empty results accurately. Default public ATS sources include Paytm and Tower Research Capital for Delhi NCR coverage.

## Acceptance
Three varied natural-language queries each return correctly-parsed, capped results. (ATS-path acceptance — a known Greenhouse-hosted company resolves via JSON API, not BS4 — applies at P2, not now.)

## Data model touched
`JobPosting` — see `data-models.md`.

## Approved web discovery extension — 11 October 2026

- Query-driven web search supplements configured boards. Its adapter can be replaced without changing scoring or chat contracts. Current adapter: Tavily basic search, at most 3 requests/search by default and 8 discovered employer pages; keys remain server-side.
- Prepare short role/skill queries from explicit filters or stored skill statements through OpenRouter. Send only search keywords and stated locations/companies to the search provider. Do not send raw resumes or identity statements.
- Fetch original public ATS/structured JDs before scoring. Reject expired structured postings where expiry is supplied, retain strict filters and tracker exclusion, canonicalize tracking URLs, deduplicate before the cap. Search snippets and inaccessible pages remain unscored external links.
- Discover indexed LinkedIn URLs through search. Seek an employer copy within the same search budget; never fetch LinkedIn, log in, or automate its UI.
- Missing/invalid keys, quota exhaustion and malformed provider responses must be visible while company boards still work.

Acceptance: isolated tests must exercise no-key/quota/authentication paths, original JD extraction, expiry, LinkedIn no-fetch behavior, employer-copy query, hard filters before capping with zero configured boards, and deduplication. Live search acceptance requires a user-provided Tavily key; until configured, mark that check pending.
