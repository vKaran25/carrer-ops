# Career Ops

## Current validation — 16 October 2026

Fresh PostgreSQL activation succeeded. Backend fixtures: **182 passed / 26 skipped**; real PostgreSQL: **12 passed**; browser fixtures: **31 passed**; live provider checks: **7 passed**; Svelte diagnostics/build passed. See [validation and remaining gates](docs/testing-2026-10-16.md). Six private resume reports are in ignored `data/test-results/2026-10-16/`.

P4 remains open for discovery coverage/relevance, four live interpretation errors, disabled Google, unverified SMTP delivery, the absent production database CA and full capacity/race acceptance. Earlier untested/activation-pending notes below describe the preceding source checkpoint and are superseded by this validation. Use `scripts/beta_access.py` for invitations; it sends no messages.

A FastAPI + LangGraph + SvelteKit job-search workspace. P4 account/queue/core UI source changes are underway; setup and acceptance are incomplete. Recorded prototype tests do not certify the new source or a production release. See [implementation evidence](docs/implementation-status.md).

## Current implementation — 16 October 2026

The focused Search chat / four-stage tracker / Settings UI, Supabase Auth/PostgreSQL adapter, invitation CLI, queue/recovery, safety caps, account deletion and Tavily-only response cache are written. They have not been tested in this pass: the user requested a separate test instruction with real DOCX resumes. PostgreSQL activation, provider setup and P4 acceptance remain pending. The old test counts and prototype descriptions below are historical.

Start PostgreSQL empty using the staged connection and explicit activation command in [Supabase setup](docs/supabase-setup.md); SQLite data is not imported. Multiple invited addresses can be managed with `scripts/beta_access.py`. See [queue, cache, limits and deletion design](docs/p4-operations.md). Put future manual test resumes in the ignored `data/test-resumes/` folder; do not commit them. Do not run the old synchronous API/browser expectations unchanged against the new HTTP 202 search-ticket contract.

## Revised release direction — 15 October 2026

The first release focuses on resume-based discovery and manual tracking for **10–15 invited testers**, with worldwide tech jobs and India as a required coverage priority. P4 implementation has started; completed increments and pending release gates are tracked separately.

| Milestone | Planned work |
|---|---|
| P4 | Harden Tavily/employer discovery; contextual search memory; focused four-stage tracker/UI; Supabase PostgreSQL/Auth, Google/email-link login, isolation, privacy and operational controls |
| P5A | Release hardening, deploy the accepted core, verify recovery/monitoring, complete documentation/demo/write-up |
| P5B / P5C | Telegram/Discord / pricing, commercial usage allowances and paid feature gates; neither blocks P5A |
| P6 | Separately accepted tailoring/cover letters, curation, interview research, MCP and optional learned scoring |

The target core hides preparation/learning and current manual LinkedIn controls, uses Interested → Applied → Interviewing → Resolved, and records Applied independently of drafts. The source now hides those prototype controls and implements four stages; this revision is unverified. Structured follow-up memory and explicit saved search defaults are implemented locally. Live interpretation, multi-user auth and PostgreSQL acceptance remain pending.

Supabase is chosen because it offers a starting free PostgreSQL/Auth tier; beta data starts empty and existing local data stays local. Session pooling, queue design, no retained backups, Tavily-only caching and initial operational caps were selected on 16 October. Hosting/capacity and actual SMTP/domain setup remain pending. Free tiers do not promise always-on availability or automatic backups. Poor Indian coverage blocks beta; Tavily plus accessible employer sources remain the initial scope, with no JSearch integration.

See the [revised SRS](docs/full-srs.md), [core acceptance](spec/core-release.md), [P4 tasks](tasks/phase-4-tasks.md), [P5 tasks](tasks/phase-5-tasks.md) and [P6 tasks](tasks/phase-6-tasks.md).


## Setup and run

Use Python 3.11 and Node 22.12+. From the repository root on macOS:

```sh
uv venv --python 3.11
uv pip sync --python .venv/bin/python requirements.lock
.venv/bin/python -m playwright install chromium
npm --prefix frontend ci
.venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

In a second terminal run `npm --prefix frontend run dev`, then open **http://127.0.0.1:5173**. API documentation: http://127.0.0.1:8000/docs. The frontend proxies /api to the backend; set BACKEND_URL in its process to use another backend address.

In Search chat, use **Add resume (.docx)** to upload a DOCX resume (the only supported upload format for now). Remove the current resume with the small × beside its filename to reveal the upload button again. Click **Find jobs** with the query empty to rank postings against your stored resume facts. Optional web discovery combines query-driven searches with your configured boards. Add an optional query to narrow the search while keeping resume fit in the ranking. The conversation is saved locally across refreshes. Search memory supports follow-ups and explicit saved defaults; New search keeps history/resume/defaults. See [memory behavior and limits](docs/search-context.md). Expand a job card to read its JD and fit explanation; click **Interested** to add it to the tracker. Search results do not enter the tracker automatically. Preparation actions are hidden and their API routes are unavailable in the current core release source. The first stage is Interested; existing Found jobs migrate there, preserving later stages. Resume upload and specific queries require a configured free OpenRouter model; searching an already stored resume with an empty query uses local embeddings; when web discovery is connected, OpenRouter also prepares short search keywords from stored skills. Local BGE embeddings download when first needed. Tectonic's first compilation may download fonts and packages.

## Nearby searches and score details

Install offline geography once with `.venv/Scripts/python.exe scripts/setup_geography.py` on Windows, then restart the backend. “Around Delhi, India” prefers 50 km and can show farther jobs in India with lower location points; “within 25 km only” is strict. Click a new result’s score for actual weighted points/evidence and distance handling. [Setup, formula and limits](docs/geography-and-fit.md). Live parser/discovery acceptance remains pending.

## Free OpenRouter configuration

Copy .env.example to .env, add your key, and select an actual current free model supporting tool calling. Settings → **Check current free tool models** reads the public catalog without a key. Select a listed ID ending in :free; openrouter/free is also accepted as the free router. Restart the backend after changing .env.

Paid model IDs are rejected before requests. Every generative call forces a function result, requires parameter support, denies provider data collection, and caps prompt/completion/per-request prices at zero. Provider errors are shown explicitly. Free model availability and quotas may change. [Free variants](https://openrouter.ai/docs/guides/routing/model-variants/free), [provider routing](https://openrouter.ai/docs/guides/routing/provider-selection).

## Optional web discovery and LinkedIn

Add `TAVILY_API_KEY` to the project `.env` and restart the backend. No new key is needed for configured public company boards or pasted imports. Tavily is a replaceable search adapter; its current free plan has 1,000 monthly credits. Basic searches use one credit each; `WEB_SEARCH_MAX_QUERIES=3` caps requests per search (the code enforces an upper bound of 6). `WEB_SEARCH_MAX_PAGES=8` bounds discovered employer pages checked. Repeated search queries reuse a 10-minute in-memory cache to save credits; original job pages are fetched again before scoring. [Provider pricing](https://www.tavily.com/pricing).

Discovery uses role/skill keywords and explicit locations/company filters. It never sends the full resume to Tavily. Search snippets are leads: scored cards require a fetched original ATS/structured job description. Expired structured listings are skipped when `validThrough` is supplied; an accessible page alone cannot guarantee that hiring remains open. Unsupported or inaccessible listings appear as external links without invented fit scores. Indexed LinkedIn leads trigger an employer-copy search within the same request budget; LinkedIn itself is never fetched by this integration.

In Search chat, click **Search on LinkedIn**, then **Open LinkedIn results** to browse the generated search yourself. **Import LinkedIn job** opens an inline form for a specific LinkedIn job URL, title, company, optional location and pasted full JD. Imports are ranked locally and saved in chat, with an explicit availability warning. Only **Interested** adds them to the tracker. Reimporting the same LinkedIn job ID preserves existing progress.

Missing search keys and provider authentication/quota failures are reported in source notices while configured boards continue working. Configure/restart the backend when ready; live Tavily discovery cannot be validated without a key.

## Current local prototype behavior

- Search real tech postings from configured company pages and optional query-driven web discovery. Initial boards: Canonical, Cloudflare, Vercel, Paytm and Tower Research Capital. Employer coverage expands dynamically when web discovery is connected; neither source guarantees exhaustive coverage.
- Required technology, role, company, industry, location and publication dates stay strict. Weak soft matches remain visible at lower fit. Unknown publication dates cannot satisfy recency. “Around Delhi” searches Delhi NCR, including Noida and Gurgaon/Gurugram; “in Delhi” keeps the city filter. Mandatory filters run before the candidate limit, and sources share the candidate pool. Scores measure content match, not hiring probability.
- Only jobs explicitly marked Interested enter the tracker and are excluded from future discoveries. A small × in Interested asks for confirmation before removing a job; its chat and activity history are retained and it can be selected again. Search never automatically tailors, curates, researches or submits applications.
- Resume uploads currently accept only .docx; other extensions and invalid Word documents are rejected. The model selects source statement IDs and categories; the backend copies the original text with source offsets. Invalid selections receive one automatic retry. The uploaded resume is treated as the user’s source of truth, without authenticity assessment. Existing saved resumes remain available until explicitly removed.
- Tailor/curate only a requested single job. Drafts select or combine whole stored statements and pass provenance validation plus an independent critic. Verified draft/JD similarity makes a small, disclosed content-fit adjustment after tailoring. No qualifications are invented.
- LaTeX curation preserves all source outside supported statement spans. PDF/Word intake uses an honestly labeled new layout. Columns/tables receive an advisory while layout stays preserved. PDF and .tex downloads are provided. Only self-contained LaTeX is supported.
- **Mark as applied** records your explicit action; it does not submit anything externally. Fix or discard a failed current draft first. Stages and outcomes persist in SQLite.
- Interview research runs on demand, uses fixed public queries, validates quoted company-specific evidence, and caches results for 60 days. Unsupported rounds/questions produce insufficient information. Public reports are anecdotal, not a guaranteed process.
- Memory consolidates current facts and explicit outcomes using add/update/delete. Local model learning stays **off**, as requested. The historical Phase 3 scorer (release deferred to P6) requires an optional prototype Settings opt-in; turning it off deletes learned weights.

Data currently lives in data/ and is excluded from Git. The running prototype remains single-user SQLite. Authentication/PostgreSQL are planned P4 work; deployment is P5A, bots P5B, monetization P5C. Current authorization covers the documentation revision; application implementation follows separately.

## Checks without LLM calls

```sh
.venv/bin/python -m pytest -q
.venv/bin/python tests/eval_harness.py --offline-engine --min-ndcg 0.8
npm --prefix frontend run check
npm --prefix frontend run build
npm --prefix frontend exec playwright install chromium
npm --prefix frontend test
RUN_LIVE_SOURCE_TESTS=1 .venv/bin/python -m pytest -q tests/test_live_sources.py
RUN_LIVE_SEARCH_TESTS=1 .venv/bin/python -m pytest -q tests/test_live_discovery.py
```

Python workflow tests run the actual API, graph, SQLite, embeddings and PDF compiler with fixture model responses. Browser tests use explicitly fictional API fixtures. They neither claim live model quality nor seed your workspace. Inspect skips if compiler/browser prerequisites are missing elsewhere.

## Real free-model acceptance after configuring .env

```sh
RUN_LIVE_QUERY_TESTS=1 .venv/bin/python -m pytest -q tests/test_query_parser.py -k live
RUN_LIVE_LLM_TESTS=1 .venv/bin/python -m pytest -q tests/test_live_workflows.py
.venv/bin/python tests/eval_harness.py --min-ndcg 0.8 --persist
```

Zero-price/privacy restrictions remain enforced. Live workflow tests use temporary databases and fictional resumes, fetch real jobs and exercise the graph, critic, explicit gate, two-JD LaTeX curation and public company research. Provider/source failures fail these tests; there is no synthetic fallback and no external application submission. Golden evaluation uses fixed fictional candidates; --persist saves EvalRun metrics locally.

Details: [parser](docs/query-parser.md), [evaluation](docs/eval-harness.md), [memory](docs/memory-and-personalization.md).

Supabase session approach selected: standard SvelteKit PKCE/cookie SDK integration, with independent FastAPI token/invitation checks. Login/database integration remains pending. [Project setup steps](docs/supabase-setup.md).
