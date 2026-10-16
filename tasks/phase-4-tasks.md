# Phase 4 — Core Search and Tracker Readiness

Status: P4 source implementation underway; separate test authorization required as of 16 October 2026. Owning acceptance: `../spec/core-release.md` and the relevant module spec. Discuss every unselected architectural decision with options and a recommendation before choosing it. All test/live-query execution now waits for the user's separate test instruction.

## 16 October implementation pass — acceptance pending

The user authorized completing P4 source work and explicitly deferred all test execution/live queries until a separate instruction with real DOCX resumes. Auth, migrations, focused UI, four stages, queue/recovery, operational counters, deletion and Tavily-only cache code are now written. These are unverified source changes; do not tick acceptance tasks or reuse the previous 189/27 counts as proof. Existing synchronous/prototype API/browser fixtures need adaptation in the separately authorized test pass.

Selected architecture: SQLModel/Alembic/psycopg with Session pooling; empty PostgreSQL schema with no SQLite import; UUID-to-owned-account mapping; operator CLI allowlist (user manages multiple addresses); one globally leased queue worker; configurable 5/account and 20/global daily search caps, 90 model and 60 Tavily attempts/day; public Tavily response cache only, 10 minutes. Immediate active deletion with no retained application backups replaces the earlier backup proposal. Both login flows are written; SMTP/domain and Google provider setup remain external configuration. See `../docs/p4-operations.md` and `../docs/supabase-setup.md`.

Staged database URL/elevated Auth key readiness confirmation is pending. Hosting/resource measurements, provider delivery, real PostgreSQL and live quality acceptance remain open. No tests were run in this pass, and P4 is not certified complete.

## 1. Baseline and evidence

- [x] Record the local prototype baseline and pending live checks; preserve current workspace data and historical tests. See `../docs/p4-discovery-audit.md`.
- [x] Inventory active/deferred UI/API routes and critical existing defects. Do not label preparation prototypes production-ready. See the audit.
- [x] Agree live benchmark contents and numerical relevance/coverage thresholds with the user before measuring release acceptance. See `../docs/discovery-benchmark.md`; live execution remains pending.

## 2. Discovery and India coverage

- [ ] Configure user-supplied Tavily/OpenRouter keys server-side; verify the selected free model's tool support and actual query/intake behavior.
- [ ] Harden Tavily plus accessible ATS/employer retrieval, non-seed discovery, provenance, deduplication, source fairness, budgets and honest failures.
- [ ] Discuss a general location-resolution approach, then implement Indian/international city and nearby-scope behavior; do not use Delhi-only logic as the solution.
  - Implemented nearby increment: offline GeoNames; preferred 50 km, broader same-country jobs allowed, 20% location credit; strict explicit radius and inline score breakdown. See `../docs/geography-and-fit.md`. Keep task open for general strict-city alias/ambiguity and live interpretation/location coverage acceptance.
- [ ] Run independently reviewed live cases spanning Indian cities/levels and independently evidenced smaller/non-seed employers plus international queries. Record relevant/eligible recovered and missed jobs, description completeness, duplicates, links, known freshness and credit usage.
- [ ] Resolve mandatory-filter/fabrication failures. Poor Indian coverage blocks beta; present the gaps and recommend a remedy before adding a provider or refining LinkedIn tooling. JSearch is not in the initial scope.

## 3. Conversational search context

- [x] Discuss context storage/API details, then implement active successful intent and explicitly saved preferences, separate from resume facts. Approved structured records/tool classifier; local implementation in `../docs/search-context.md`. Production account binding/migrations remain open.
- [x] Implement follow-up overrides, new-intent handling, ambiguity clarification, preference correction/deletion and reset that retains history/resume. Fixture acceptance recorded separately from live-model acceptance.
- [ ] Complete failure/cancellation/reconnect acceptance. Effective filters, parser/source-failure preservation, revision protection and stale resume-score invalidation are implemented; durable cancellation/execution remains pending.
- [ ] Verify follow-ups across refresh/login, isolation, errors and contradictory/new instructions.

## 4. Focused tracker and release boundary

- [ ] Keep Search chat / Job tracker / Settings and approved inline DOCX/JD controls.
- [ ] Hide preparation, research, curation, learning, MCP and unfinished-feature controls; enforce the same availability boundary on production APIs.
- [ ] Hide current manual LinkedIn buttons initially; preserve imported/history data and no-scraping rules.
- [ ] Implement Interested → Applied → Interviewing → Resolved; keep explicit audited/idempotent intake, manual stages/outcomes, and confirmed Interested removal/restore.
- [ ] Make core Mark as Applied independent of dormant draft/critic results. Back up and test legacy Tailored → Interested migration in an isolated copy, preserving artifacts and Applied/later progress.
- [ ] Separate ordinary user Settings from operator credentials/global administration. Discuss any additional structural UI choices first.

## 5. Accounts and production persistence

- [ ] Configure Supabase PostgreSQL/Auth starting free; review current limits, inactivity behavior and missing automatic backups with the user.
- [ ] Discuss session/token, invitation-management and identity-mapping designs before implementing. Support Google and passwordless email links; agree SMTP provider/domain and actual mail delivery setup.
- [ ] Enforce invitation eligibility on the server for 10–15 users. Later public admission must use the same identity/ownership model.
- [ ] Replace hardcoded user 1 across private resources and configuration. Verify access to jobs, tracker, history/context, resume, artifacts, memory and sources on direct API paths.
- [ ] Introduce versioned PostgreSQL migrations and transactional audit guarantees; do not rely on runtime create_all or SQLite-only triggers as production migration/enforcement.
- [ ] Start beta empty. Keep local data intact; no automatic owner-data import.
- [ ] Implement signup/intake privacy notices and account deletion. Agree backup-retention and artifact deletion semantics with the user first.

## 6. Operational readiness

- [ ] Measure actual embedding/browser memory, warm latency, cold starts and source/model usage. Recommend hosting options and agree the vendor/topology before P5A.
- [ ] Discuss execution/recovery architecture and idempotency before implementing durable search status, reconnect/retry and interrupted-run recovery.
- [ ] Agree workload/concurrency, per-operation limits and global provider budgets for 15 accounts. Enforce operational abuse/credit protection without introducing paid tiers.
- [ ] Verify safe diagnostics, readiness and rollback/recovery behavior. The user selected no retained application backups on 16 October; backup storage/restore acceptance is deferred by that decision. Hosting/monitoring integration still needs a reviewed choice.

## 7. Acceptance before P5A

- [ ] Meaningful core/backend/browser checks plus actual configured free-model and live-source validation, with fixture/live evidence clearly separated.
- [ ] Real PostgreSQL migration, isolation, concurrent action/audit and deletion checks. Backup restore is excluded by the current no-backup decision.
- [ ] Desktop/mobile, stale resume, empty/partial/failure/quota and deferred-route visibility/denial checks.
- [ ] User review of live Indian coverage against agreed thresholds; failed coverage or unresolved integrity/recovery issues keep the beta gate closed.
- [ ] Record measured 15-account capacity/workload and remaining platform limits. Obtain the planned release approval after the deployable result and evidence are concrete.

No P6 preparation, MCP, learned scoring, bot or pricing work is required to satisfy this phase.

Session checkpoint selected: standard Supabase SvelteKit PKCE/cookie integration, backend token/invite validation. Implementation and live provider/DB acceptance remain pending. User setup: `../docs/supabase-setup.md`.
