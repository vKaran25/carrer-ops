# Implementation and acceptance status

## 16 October 2026 — authorized validation completed; P4 acceptance open

See [current test report](testing-2026-10-16.md). Fresh PostgreSQL schema activation succeeded. Backend fixtures: **182 passed / 26 skipped**; isolated real PostgreSQL: **12 passed**; browser fixtures: **31 passed**; live provider checks: **7 passed**; Svelte diagnostics/build passed. All six DOCX resumes extracted exact source-backed facts. Private per-resume reports and logs are under `data/test-results/2026-10-16/`.

Default resume searches returned ten results per case with recorded live keyword responses replayed and live sources/ranking; explicit queries returned 8/0/0/0/0/3. Senior/lead relevance, overconstrained role phrases, four interpretation errors and weak fixed-benchmark coverage remain unresolved. Google is disabled, SMTP delivery is unverified, and the production CA certificate is absent. These findings keep P4 open. Earlier “tests deferred / untested” sections below are historical checkpoints, superseded by this validation.

## 16 October 2026 — new P4 source changes, tests deferred

The user authorized completing P4 implementation and requested that all tests/live queries run separately, only after a later instruction with real DOCX resumes. The new source includes a focused core UI/four-stage tracker, deferred API denial, Supabase PKCE login and backend identity/invitation checks, fresh Alembic PostgreSQL schema, persisted search queue/recovery, usage caps, account deletion and a ten-minute public Tavily response cache. General location matching, source-location consistency and description guards were also revised.

**These source changes are untested.** No backend/browser suites, Svelte checks, builds, live model/source queries, PostgreSQL acceptance or personal-resume runs were executed in this pass. The previous test counts below apply to the earlier code. Existing synchronous/prototype fixtures need adaptation during the separately authorized test pass. Source completion is not phase acceptance.

PostgreSQL activation is staged behind the user's connection/key-ready notification. No SQLite data is imported. The user will manage multiple invitation emails through the CLI. Google configuration and SMTP/domain delivery are external setup. The user selected immediate active deletion with no retained application backups. See [Supabase setup](supabase-setup.md) and [operating design](p4-operations.md). P4 remains open for setup, security/recovery/capacity validation and user-reviewed discovery quality.

## Revised release direction — 15 October 2026

Latest validation: [15 October live/local test report](testing-2026-10-15.md). Tavily is now configured and passed a real provider check; the preview backend was restarted to load it. Default backend: 1812 passed/11 skipped; browser fixtures: 27 passed; Svelte/build passed. Six live search/source checks and fictional resume extraction passed, as did targeted live follow-up and nearby parser probes. The twelve-case discovery capture did **not** meet coverage: seven scored results across eight Indian cases, none with three results; London/Berlin/Toronto raised GeographyError. Scope interpretation and contradictory source-location issues were exposed. Independent quality review remains pending, and Supabase Auth/PostgreSQL is still unimplemented. This supersedes pending-Tavily-key notes below; it does not establish P4 acceptance.

**P4 implementation started; discovery, nearby scoring and structured-memory increments implemented locally. P4 release acceptance is incomplete.** The sections below retain earlier prototype evidence, UI decisions and live limitations. Do not use old phase assignments or old UI descriptions as the current release scope.

- Core release: resume discovery, source-backed chat results, contextual follow-ups and four-stage manual tracking. P4 adds core hardening, live Indian/worldwide coverage, Supabase PostgreSQL/Auth, Google/email-link login, invitation eligibility, isolation, privacy and operational protection.
- Beta target: 10–15 invited testers; empty authenticated workspaces, with local data untouched. Public registration must later use the same identity model.
- P5A retains hardening/deployment/documentation/demo/write-up. P5B bots and P5C pricing/commercial allowances/paid feature gates follow without blocking deployment.
- Preparation, interview research, MCP and learned scoring release in P6. Existing prototype code/data/tests are retained; target UI hides controls and production APIs deny deferred actions. Focused UI/API gating and stage migration are still pending.
- Saved history now has a structured follow-up/default-preference layer and offline nearby scoring. Live interpretation, Supabase accounts/PostgreSQL, general strict-city matching, the four-stage migration and Indian release-coverage acceptance are **pending P4 work**. Tavily requires the user's configured key for live validation.
- The core initially uses Tavily plus accessible employer sources, not JSearch. Poor Indian coverage blocks beta and triggers a reviewed remedy. Current manual LinkedIn controls will be hidden in the target core pending any refined feature decision.
- Supabase has a starting free tier (verified 15 October); SMTP, hosting/execution/backup design and numerical operating limits still require user discussion; the initial discovery benchmark gates are approved. Local learned scoring remains OFF.

Authoritative requirements: [SRS](full-srs.md), [core release acceptance](../spec/core-release.md). Execution lists: [P4](../tasks/phase-4-tasks.md), [P5](../tasks/phase-5-tasks.md), [P6](../tasks/phase-6-tasks.md).

Historical documentation-only validation before implementation: **25 Markdown-only files**, 21 local Markdown links and 57 document references checked; code fences balanced, SRS sections 0–15 retained, upgrade phase ownership and P4/P5/P6 task lists checked; `git diff --check` passed. Application code, UI, data and runtime configuration were not changed, so application test suites were not rerun. This is documentation acceptance only.

## Original scope and decisions — historical record

The original checkout contained a backend health scaffold, query parser and partial evaluation harness. The user authorized restoring Phase 1 prerequisites and implementing through Phase 3, including UI and acceptance tests. That original scope has been superseded by the release roadmap below; its test evidence remains historical.

UI: light blue workspace, sidebar Search / Job tracker / Resume / Settings, details beside results, Kanban/list toggle. Worldwide tech postings from configured sources. Local embeddings approved. Strict hard filters, lower-scoring soft matches retained. Exact stored statements only for drafts/curation. Preserve LaTeX layout with a column/table advisory. Only free OpenRouter models. Isolated fictional fixtures allowed. Local outcome-based learning stays off at the user's request; its consent-gated implementation is available for later use.

## Acceptance evidence

| Module | Implementation and checks | Live limitation |
|---|---|---|
| P1 graph / getting started | Real API/graph search → tailor → critic → explicit gate tests; optional resume | Real model loop pending key |
| P1 scout | Posting contract, varied query fixtures, static crawler, caps and tracker deduplication tested | Public ATS checks passed |
| P1 tailor / critic | Two distinct JD drafts, exact fact IDs, planted fabrication rejection; verified draft contributes to content fit | Actual model selection/criticism pending key |
| P1 gate | Explicit action, persistent audit, SQLite status triggers; API false-action and direct database bypass rejection tested | No external submissions |
| P1 tracker | Five stages, outcomes, Kanban/list; fresh-session storage and browser reload/update tests | Local single-user scope |
| P2 query | Five distinct forced-tool parser fixtures and invalid-tool/schema checks | Live five-query extraction pending key |
| P2 scoring | Actual local embeddings, grounded signals, strict filters, soft relaxation; adversarial dates, Java/JavaScript, unknown tier and impossible hard filters tested | Golden set is fictional and small |
| P2 ATS | Greenhouse/Lever/Workday JSON first, BS4 then logged Playwright; actual Chromium JS fixture passed | Real Canonical/Vercel/Cloudflare, Spotify and NVIDIA source checks passed |
| P2 research | Fixed queries, single synthesis, company filtering, exact evidence, shared 60-day cache and explicit insufficient-data checks | Live documented/obscure-company acceptance pending key and source availability |
| P2 curator | Stable IDs/spans, exact-fact edits, critic, PDF/tex, honest template fork and ATS advisory; two-JD edits preserve surrounding source; real Tectonic render/download/extraction tested | Actual model plans pending key |
| P3 memory | Stable source keys and add/update/delete; replacements, corrections and deletion tested | No invented facts/outcomes |
| P3 scorer | Per-user bounded batch model, six-outcome cold start, five-new-outcome/on-demand refit; fixture ranking changes, user isolation, opt-in/revocation tested | OFF in real workspace as requested |
| P3 evaluation | Tool/spec metrics plus actual ranking adapter, optional EvalRun persistence and adversarial filter tests | Real parser benchmark pending key |
| UI | Four responsive pages, empty/error states, explicit actions and provenance; 13 Chromium checks pass | Browser API responses are fictional fixtures |

## Recorded results

- Backend suite: **93 passed, 9 skipped** in the default run (5 public-source and 4 real-model opt-in checks).
- Public source suite: **5 passed** for Greenhouse, Lever and Workday. A separate real API/graph keyword search returned three real postings without source warnings in an isolated database.
- Actual local ranking with replayed parser: **5 cases**, P@2/R@2 **0.900**, NDCG@2 **0.965**.
- Browser suite: **13 passed**.
- Svelte diagnostics: **0 errors, 0 warnings**.
- Production frontend build: **passed**.
- Browser smoke check against the actual backend: all four pages opened, zero JavaScript errors, local learning confirmed off.

Replayed parser tool/spec accuracy is 100%; this is not live LLM accuracy. The Java/fintech benchmark ranks an older eligible role above one labeled banking role. There is no recency hard filter in that case; labels were not changed to improve the result. Scores are not empirical hiring probabilities.

## Current live acceptance — 11 October 2026

The Windows workspace is configured with `cohere/north-mini-code:free`. Real OpenRouter calls passed the five-query acceptance, the search/resume/tailor/critic/explicit-gate workflow, and the five-case golden evaluation (100% tool/spec accuracy; NDCG@2 0.965). Privacy and zero-price restrictions remained enforced. The latest default backend suite passed 93 tests with 9 opt-in live checks skipped; all 13 browser fixture checks, frontend diagnostics and build passed. Five public-source checks passed in the source-enabled run.

Full live acceptance through P3 remains **not certified**: two-JD curation failed (initially identical output, then provenance rejection on a targeted rerun), and well-documented-company research failed grounded-evidence acceptance. Tectonic is installed; compiler/layout fixture checks passed after a Windows newline preservation fix. Local learning remains disabled. Successful query/search checks do not certify the model's curation or research quality.

See [the current test report and manual checklist](testing-2026-10-11.md). The module table and recorded results above describe the earlier implementation run; this section supersedes their pending-key notes. [README](../README.md) provides opt-in commands for the live tests.

Practical limits: configured and bounded source coverage; unknown publication dates cannot satisfy recency; public APIs/search may change or block access; scanned PDFs and arbitrary LaTeX macros/external files are unsupported. The workspace is local and single-user.

## Resume search on the main page — 11 October 2026

User-requested flow: Add/Replace resume and exact fact review now live on Search jobs; the separate Resume navigation item is removed and old `/resume` bookmarks redirect to `/#resume`. An empty query searches configured sources with local resume ranking and no query LLM call. A specific query adds filters/preferences while retaining resume fit. The resume mode rejects missing stored facts; upload/removal clears stale results, and rejected replacements retain the current profile. Existing keyword/natural API modes remain compatible.

Validation: focused backend workflow/parser/scoring suite **34 passed, 1 opt-in live check skipped**; browser fixture suite **15 passed**; Svelte diagnostics **0 errors, 0 warnings**; production build **passed**. These checks cover resume ranking, optional-query filters, duplicate tracking, intake/removal, failed replacement, redirect, and desktop/mobile layout. No new personal-resume upload or live provider quality check was performed for this UI change; prior curation/research limitations still apply.

## Saved search chat and explicit interest — 11 October 2026

Confirmed by the user: one saved continuous chat; inline collapsible job descriptions/fit; preparation actions only in the tracker after Interested; migrate existing Found entries to Interested. Search persists JD records and a ChatTurn snapshot without creating applications. Interested validates the selected job against its search message, records the action, and creates one application; repeat clicks retain later progress. Only chosen jobs are excluded from future discovery. Chat history follows tracker stages across reloads, and outdated resume scores are cleared after resume changes.

Current validation: backend **100 passed, 9 opt-in live checks skipped**; browser fixtures **17 passed**; Svelte **0 errors, 0 warnings**; production build **passed**. Checks include saved/repeated queries, no automatic applications, explicit interest/retry/idempotence, preparation gating, stale resume evidence, migration preserving later stages, original applied audit restrictions, and mobile accordions/composer. Live provider quality was not retested; earlier curation/research limitations remain.

Actual workspace migration: **30 Found → Interested**, with 30 migration audit entries and zero remaining Found entries. A SQLite backup was created at `tmp/backups/career_ops_before_chat_20261011_132726.sqlite`. A read-only browser check against the real backend verified the resume, 30 Interested cards, preparation availability and zero JavaScript errors. Earlier search queries were not stored, so they were not fabricated into chat; new successful searches start the saved conversation.


## Tracker layout repair and DOCX intake — 11 October 2026

Restored the original tracker layout CSS that the prior removal-button edit accidentally replaced. Interested cards have a small sibling × in Board and List, with a native confirmation dialog (Cancel, Remove job, keyboard focus management). Removal persists as dismissed, keeps chat/JD/audit history, excludes the record from visible tracker counts, and permits explicit re-selection from chat; later stages cannot be removed using this action. Successful removal refreshes workspace counts.

Resume controls show the current filename with a small remove ×. There is no Replace resume button or duplicate removal action in the fact summary. After removal, Add resume (.docx) appears. New uploads accept only DOCX for now; client validation and the API reject other extensions, and malformed DOCX documents are rejected without overwriting an existing profile. Existing stored resumes remain available. Removing a resume retains chat and clears stale fit data.

Validation: backend **102 passed, 9 opt-in live checks skipped**; browser fixtures **21 passed**; Svelte **0 errors, 0 warnings**; production build **passed**. Checks cover removal confirmation/cancel, persistent dismissal, re-selection, applied-stage protection, DOCX parsing/invalid input, resume removal and upload-button restoration, stale scores, and desktop/mobile layout. Screenshots were visually inspected. A read-only smoke check of the running app confirmed 30 tracker cards, the resume ×, restored grid styling and zero JavaScript errors; a job-removal dialog was opened and cancelled. No personal resume was removed or uploaded during validation, and live provider quality was not retested.


## Resume extraction by source statement ID — 11 October 2026

Approved fix: segment extracted resume text into source statements with IDs and offsets; the OpenRouter model selects only IDs and categories, and the backend copies the original text. The extraction schema no longer permits AI-written evidence/claims. Whitespace, punctuation and Unicode remain identical to source slices. Unknown IDs and malformed schema selections receive one bounded retry; persistent failures display a neutral request to upload the DOCX again. Provider/configuration failures retain their existing error path. Failed uploads preserve any currently stored profile.

The uploaded resume is treated as the user's source of truth. Intake does not assess the plausibility or authenticity of their qualifications. UI labels now say resume statements/details instead of verified facts. Existing resume ranking already matches the approved recommended behavior: relevance to stored resume content, partial matches visible, explicit query filters enforced, no requirement that the resume satisfy every JD condition. Exact stored-data restrictions on generated tailoring remain in place.

Validation: default backend suite **110 passed, 10 opt-in checks skipped**; browser fixtures **21 passed**; Svelte **0 errors, 0 warnings**; production build **passed**. A targeted real free-OpenRouter extraction test **passed** using fictional input with unusual punctuation and spacing; copied facts matched source offsets exactly. No personal resume was uploaded/removed for this test and no workspace records were replaced. The backend was restarted with the fix. This focused extraction acceptance does not certify the earlier unresolved live curation/research acceptance.


## Delhi search diagnosis and discovery repair — 11 October 2026

The two saved queries asked for jobs around Delhi. Both were parsed to Delhi and each excluded 200 candidates for location, with zero source failures. Live inspection confirmed the original three sources (Canonical, Cloudflare, Vercel) had no stated Delhi/NCR locations. Discovery also capped the aggregate before checking mandatory filters, allowing the first company to consume the candidate pool.

Fixed discovery to filter all retrieved postings before the cap and interleave matching sources. Added Delhi/New Delhi and Gurgaon/Gurugram equivalence; explicit around/near Delhi requests map to Delhi NCR, while city-only Delhi filters stay strict. Added verified public Paytm (Lever) and Tower Research Capital (Greenhouse) boards, preserving existing source configuration. Included AI/ML and analytics titles in technical-role detection. No company industry/tier metadata was inferred.

Search snapshots now retain retrieval/filter/tracker diagnostics. Chat shows source coverage and source notices; empty messages distinguish missing sources, failed/empty retrieval, location/other-filter exclusions and fully tracked results. Historical empty turns receive explanations from their recorded filters without rewriting their queries or results.

Validation: **127 backend tests passed, 10 opt-in checks skipped**; **22 browser fixture tests passed**; Svelte **0 errors, 0 warnings**; production build **passed**. Regression cases cover matches after 300 irrelevant early postings, later-source fairness, strict/nearby city scope, unknown locations, deduplication and honest empty-state notices.

A real rerun of `find jobs according to my resume around delhi` used the configured free query model and the user's stored local resume ranking. Across five sources, it retrieved **1,098 postings**, identified **477 tech roles**, excluded **458** by location, and found **19** eligible NCR roles. The top **15** were saved to chat (turn 3), with stated locations in Noida and Gurgaon. Tracker counts were unchanged. An actual browser check confirmed 15 job cards, coverage labels and zero JavaScript errors; screenshot: `tmp/delhi-search-ui.png`. Source coverage remains the configured company boards, and current vacancies may change.


## Dynamic web discovery and LinkedIn chat integration — 11 October 2026

Implemented the approved three actions: optional query-driven web discovery, Search on LinkedIn, and inline LinkedIn job import. Tavily basic search is a replaceable provider adapter with a default 3-query/search limit (enforced maximum 6), 8 discovered employer pages (maximum 20), and a 10-minute in-memory repeat-query cache keyed by a hash of provider key and query. Search queries use explicit role/technology filters or short OpenRouter-prepared keywords from stored skill statements; raw resumes and identity statements are not sent to Tavily.

The scout supplements configured boards with dynamically discovered Greenhouse/Lever boards or individual listings and structured JobPosting pages. Original descriptions are required before scoring. Structured expiry dates are honored when supplied; availability is otherwise not guaranteed by retrieval. Search snippets and inaccessible/nonstructured pages appear as external links without scores. Indexed LinkedIn leads trigger an employer-copy query within the same budget. LinkedIn links are never fetched: the public fetch validator also blocks employer redirects and browser routes to LinkedIn. Required filters, active-tracker exclusion, canonical URL deduplication and filtering before the cap apply to the merged candidate pool. Missing keys, auth failures and quota failures leave configured boards functional and show clear source notices.

Search on LinkedIn prepares an encoded external link from the current query or resume skills. The user opens it manually. Import accepts a specific HTTPS LinkedIn job URL plus pasted title/company/JD and optional location. Its form lives in the scrollable conversation, preserving the composer. Imported jobs receive local resume ranking, saved chat snapshots and an expanded unverified-availability notice. Interest remains explicit; canonical job IDs prevent duplicate tracker records and preserve later stages on reimport. These actions do not submit applications or trigger preparation.

Validation: **147 backend tests passed, 11 opt-in live tests skipped**; **25 browser fixture tests passed**; Svelte **0 errors, 0 warnings**; production build **passed**; diff whitespace check passed. New isolated cases cover URL/domain validation, no-key/auth/quota behavior, cached calls/basic-search-only requests, original-JD extraction, expired listings, no LinkedIn fetch including redirects, employer-copy searches, zero-configured-board discovery, strict filters before capping, saved import/Interest gating, idempotent reimport preserving Applied, LinkedIn search keyword encoding, no identity in planning inputs, and desktop/mobile controls. An initial collapsed import warning and crowded composer layout were corrected before the final browser rerun.

Live OpenRouter handoff checks passed on the running backend: `Java backend jobs in Pune` produced keywords/location in the LinkedIn search URL; an empty query produced keywords from the user's stored resume skills. These checks created no chat or tracker records. A read-only browser inspection against the real backend confirmed the import controls, zero JavaScript errors and no horizontal overflow at 390px. Screenshots: `tmp/linkedin-chat-live-desktop.png`, `tmp/linkedin-chat-live-mobile.png`. The backend was restarted with the changes.

**Pending user setup:** TAVILY_API_KEY is absent; the user chose to add it later. Real Tavily discovery has not been claimed as tested. Once added, restart and run PowerShell: `$env:RUN_LIVE_SEARCH_TESTS="1"` then `.venv/Scripts/python.exe -m pytest -q tests/test_live_discovery.py`. This opt-in test uses real search/original-page fetches without modifying the user's database. Earlier live curation/research limitations remain separate.

## P4 discovery, geography and memory increment — 15 October 2026

Implemented source-boundary fixes, a 12-case capture/independent-review benchmark, offline GeoNames nearby lookup and 80/20 score contributions, clickable persisted breakdowns, and the approved structured intent/default-preference layer with reset and revision guards. Detailed evidence/limits: [audit](p4-discovery-audit.md), [geography](geography-and-fit.md), [memory](search-context.md), [benchmark](discovery-benchmark.md).

Latest backend regression run: **1812 passed, 11 opt-in live checks skipped**. Svelte: **0 errors, 0 warnings**. Browser full suite: **27 passed** (fictional fixtures); production build **passed**. Fixtures use temporary databases and fictional profiles; GeoNames lookup checks use the actual downloaded index without user resumes. No real Tavily search or new live model acceptance is claimed. The user will add the key and notify when ready. This increment does not complete P4.

Selected next auth approach: standard Supabase SvelteKit PKCE/cookie integration with backend token/invite verification. The user still needs to create the project; [setup instructions](supabase-setup.md). The runtime adapter is not implemented yet. Final documentation check: 30 Markdown files, 34 local links and balanced fences passed; `git diff --check` passed. Final focused score/memory UI rerun: **2 passed** after the sticky accordion-summary adjustment.
