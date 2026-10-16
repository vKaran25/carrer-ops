# Core production release `[P4 / P5A]`

Approved direction: 15 October 2026. This is a target specification, not a claim that the local prototype implements it. P1–P3 test evidence remains historical. P4 acceptance precedes P5A deployment; P5B/P5C and P6 do not block that deployment.

## Decisions confirmed 16 October 2026

Use SQLModel/Alembic/psycopg with Supabase Session pooling and a fresh database schema; no SQLite data import. Use verified UUID account mapping, an operator CLI invitation allowlist, a PostgreSQL queue with one globally leased FastAPI worker, saved status/cancel/explicit retry, and the agreed operational defaults (5/account and 20/global searches, 90 model attempts, 60 Tavily attempts per UTC day). Cache only public Tavily responses for ten minutes; descriptions and private ranking/context/tracker data are not shared/cached as results.

The user selected immediate active deletion with **no retained application backups**. Earlier backup/restore gates below are superseded for this initial scope; recovery covers interrupted executions and compatible application rollback, not guaranteed database-loss restoration. Both login flows are written in source; actual Google configuration and later Resend SMTP/domain setup remain external. See `../docs/p4-operations.md`.

Tests, builds, real queries, PostgreSQL acceptance and personal resume runs are explicitly deferred until the user's separate instruction. Source implementation does not mark this phase accepted. PostgreSQL activation also waits for the staged connection/key-ready notification.

## Confirmed release boundary

- Resume-based worldwide tech discovery, India priority; saved Search chat with follow-up context; explicit Interested; four-stage manual tracking; Settings and account/privacy controls.
- DOCX-only upload with exact source statements, current-filename/remove × controls, local embeddings, optional query and strict mandatory filters. Scores describe content match, never hiring probability.
- Tavily plus accessible configured/discovered employer sources initially. No JSearch integration. Public platform links do not establish full-platform coverage or permission to scrape LinkedIn.
- Tailoring, cover letters, curation, preparation critic, interview research, MCP and outcome-based learned scoring are P6. Preserve existing prototype code/data, hide controls and deny deferred production actions through a centralized feature-availability policy.
- Hide current manual LinkedIn buttons in the target core UI; a refined LinkedIn feature needs a later decision based on coverage evidence. Incomplete public leads may remain separately labelled and unscored.

## Search quality and execution

- FR-CORE-1: One Find jobs action uses the current resume and effective query across enabled sources. Discover employers beyond the initial seed list; adding company URLs must not be required for ordinary searches.
- FR-CORE-2: Normalize and deduplicate using source job identifiers/canonical URLs while preserving attribution and distinct requisitions. Apply mandatory filters before caps; avoid first-source dominance.
- FR-CORE-3: Score only descriptions supported by retrieved source evidence. Preserve publisher, original/apply links, known posting/expiry dates, retrieval time, and uncertainty. Snippets alone cannot become a scored full JD.
- FR-CORE-4: Support general country/city/nearby-area interpretation. Unknown location/date cannot satisfy a mandatory constraint. Resolve geographic ambiguity rather than silently broadening; remove Delhi-only assumptions from the general solution.
  - Approved nearby design: offline GeoNames; default 50 km preference with same-country broadening, adjustable via query. Location earns 20% of fit; other relevance keeps 80%. Full credit inside radius, radius/distance outside, zero for unknown distance. Explicit distance boundaries stay mandatory. Display effective scope and inline actual score contributions/evidence/unknowns.
- FR-CORE-5: Keep weaker eligible matches visible. If none qualify, report an honest empty state with checked coverage and failures. No unconditional nonempty-result guarantee.
- FR-CORE-6: Bound calls, page fetches, concurrency and retries; explain missing keys, partial source failures, quota exhaustion and interrupted runs. Persist enough execution state for refresh/reconnect and idempotent retries without duplicate conversation turns or tracker intake.
- FR-CORE-7: Provider queries contain necessary search terms, not raw resumes or identity statements. Treat retrieved text as data, never instructions to invoke tools or change user constraints.

## Conversational search memory

- FR-CTX-1: Persist account-scoped history, active search context and explicitly saved preferences. Keep them distinct from exact resume facts and observed job data.
- FR-CTX-2: Resolve follow-ups such as “same role, but in Delhi” against the last successful search intent. New explicit constraints override the same prior field; unrelated standalone searches start a new intent. Saved preferences remain visible and overridable.
- FR-CTX-3: Ask when a reference or location is ambiguous. Failed or cancelled searches must not silently replace the last successful context. Do not infer permanent preferences or qualifications from job descriptions or casual dialogue.
- FR-CTX-4: Show effective constraints and offer reset/new-search plus preference edit/remove controls. Reset preserves resume and history. Resume changes invalidate old fit information and resume-derived context, while explicit user preferences remain available.

## Tracker and UI

- FR-CORE-TRACK-1: Search creates zero applications. Explicit Interested creates one audited application idempotently, and repeated selection preserves later progress.
- FR-CORE-TRACK-2: Expose Interested → Applied → Interviewing → Resolved with manual updates and outcomes. Applied always needs its explicit action and audit record, independent of deferred drafts/critic results; it does not submit externally.
- FR-CORE-TRACK-3: Preserve confirmed Interested removal/restore behavior and chat/audit history. Migrate legacy Tailored to Interested with an audit entry, retain preparation artifacts, and leave Applied/later progress intact.
- FR-CORE-UI-1: Keep the approved light blue Search chat / Job tracker / Settings structure and responsive JD accordions. No preparation, learning, MCP, plan/pricing or unfinished feature controls in the core UI.
- FR-CORE-UI-2: User Settings expose preferences, account/privacy and understandable service status. Operator key/model/source administration must not expose credentials or global configuration to ordinary users.

## Accounts, persistence and operations

- FR-CORE-AUTH-1: Google and passwordless email-link authentication via Supabase Auth; invite-only access for 10–15 testers enforced server-side. Public registration later reuses the same account model.
- FR-CORE-DB-1: Supabase managed PostgreSQL, starting free. Use versioned migrations and real PostgreSQL acceptance; remove hardcoded user 1 from production ownership paths. SQLite remains a local prototype/development option, not the deployed account store.
- FR-CORE-DB-2: Require authenticated ownership for every resume, source configuration, chat/context, job/application, artifact and memory operation. Preserve Applied audit invariants on PostgreSQL. Test direct cross-user resource access and concurrency.
- FR-CORE-DB-3: Start the beta empty. Existing local data remains local; any owner import is a separately authorized, backed-up migration.
- FR-CORE-OPS-1: Enforce operational abuse protection, per-operation budgets and global provider caps before deployment. These apply without paid tiers. Numerical limits must be agreed from measured provider/resource capacity for the beta.
- FR-CORE-OPS-2: Health/readiness checks, safe diagnostics, monitoring, recovery of interrupted searches, deploy rollback and the explicitly selected backup/no-backup policy are release requirements. Do not log raw resumes, access tokens or keys.
- FR-CORE-PRIV-1: Explain external processing at intake and privacy at signup. Support deletion of the account and associated workspace/context/artifacts; honor the selected no-retained-application-backup deletion policy. No training without separate opt-in.

Supabase selection satisfies the user's “Supabase if a starting free tier exists, otherwise Neon” decision. On 15 October 2026 the free plan includes PostgreSQL/Auth, with 500 MB database storage, inactivity pausing and no automatic backups. Recheck limits at setup; a free plan does not establish always-on availability. [Pricing](https://supabase.com/pricing).

Real email-link delivery needs custom SMTP; the built-in sender is restricted to project team addresses. Session design selected: standard Supabase SvelteKit PKCE/cookie SDK integration, with independent FastAPI token/invite validation; source written, setup/acceptance pending. User setup: `../docs/supabase-setup.md`. Session pooling, queue, cache, operational values and no retained backups were selected on 16 October. Actual SMTP/domain setup and hosting/capacity review remain pending checkpoints. Recommend options with evidence before choosing. [Email delivery requirements](https://supabase.com/docs/guides/auth/auth-smtp).

## Acceptance and release gates

1. **Evidence:** keep prototype/fixture checks separate from live model, live source, PostgreSQL and deployed-system evidence. Pending acceptance remains pending.
2. **Core flow:** upload → search → follow-up → inspect source-backed JD → Interested → manual application stages survives refresh, logout/login and server restart; duplicate requests do not duplicate intake.
3. **Memory:** verify overrides, standalone queries, ambiguity, reset, explicit preference correction/deletion, failed searches, resume changes and account isolation.
4. **Coverage:** maintain a fixed, independently reviewed live benchmark spanning Indian cities/levels, non-seed employers including smaller employers where independently evidenced, plus international queries. Record relevant results, known eligible vacancies recovered/missed, strict-filter violations, usable-description rates, duplicates, valid source links, freshness and provider credits. Do not infer company size from unknown metadata.
5. **Coverage gate:** mandatory-filter violations, invented evidence or poor Indian coverage block beta. Present measured quality and proposed numerical pass thresholds to the user for approval before evaluating the release. If Tavily is inadequate, revisit providers with the user; do not silently add JSearch or fall back to manual browsing as the main product.
6. **Data:** verify real PostgreSQL migrations, isolation, concurrent writes, audit enforcement, deletion and queue/application recovery. Backup restore is excluded by the current user-selected no-backup policy. No legacy data import is required for the fresh PostgreSQL workspace.
7. **UI and failures:** verify desktop/mobile, loading/error/empty/partial states, provider quota/auth errors, stale resume scores, and absent deferred controls/direct API access.
8. **Deployment:** agree the concurrency/workload profile for 15 accounts, test actual embedding/browser/resource needs and free-tier limits, then record the hosting decision with the user before P5A. Unknown capacity or failed recovery blocks launch.
9. **Public transition:** validate registration mode, access control, abuse protection, budgets and capacity before opening signups. No identity/data-model rebuild should be required.
