# Core readiness, deployment and upgrades

Revised 15 October 2026. P4 is focused on the core search/tracker release, not bots, monetization or MCP. See `core-release.md` for its complete requirements and acceptance. Historical prototypes are not released merely because functions exist.

## Facts, history and context `[P3 / P4]`

- FR-MEM-1: Consolidate exact resume facts and explicitly logged outcomes by stable source identity, supporting add/update/delete. Stored outcomes do not enable learning.
- P3 saved history is implemented as search/result snapshots; conversational follow-up interpretation is a new P4 requirement.
- FR-CTX-1–4: Persist account-scoped active search intent and explicitly saved preferences, resolve follow-ups/overrides, clarify ambiguity, expose correction/reset, and invalidate stale resume evidence. See the owning core spec for acceptance.
- FR-MEM-2 (learned weights) moves to P6; local learning remains OFF.

## Evaluation `[P3 / P4]`

- FR-EVAL-1: Golden tool/spec and ranking checks plus an independently reviewed live India/international discovery benchmark.
- FR-EVAL-2: Weak soft matches stay visible; impossible hard filters yield honest empty states. Never require nonempty fabricated/mandatory-violating results.
- Separate fixture, live-model/source, PostgreSQL and deployment evidence. Agree numerical coverage/performance thresholds with the user; poor Indian coverage blocks beta.

## Core readiness `[P4]`

- Supabase PostgreSQL/Auth (free starting tier), Google + passwordless email-link login, server-enforced invite-only admission for 10–15 testers, verified user isolation and clean beta workspaces.
- Versioned migrations, PostgreSQL Applied audit enforcement, private artifact/source/context access, deletion and explained data processing.
- Core UI: Search chat / Job tracker / Settings; four stages Interested → Applied → Interviewing → Resolved. Hide deferred preparation/learning/MCP and current manual LinkedIn controls; deny deferred production routes.
- Operational limits, bounded provider budgets, honest partial/quota errors, persistent execution status, safe diagnostics and recovery requirements apply before monetization.
- Hosting, SMTP, session/invitation/worker architecture, backups/retention and limit values are user decision checkpoints. Do not silently select them.

## First release `[P5A]`

Complete final hardening, deploy after P4 acceptance, validate monitoring/recovery/rollback, and publish setup/operator documentation, demo video and write-up. Free-tier limitations must be explicit; do not promise always-on service or backups not provided by the plan. Opening public registration later requires capacity/budget/abuse checks using the same account model.

## Additional clients `[P5B]`

- FR-BOT-1: Telegram/Discord use the same authenticated orchestrator, scores and manual tracker gates.
- Discuss account linking, supported commands, credentials and access boundaries at the milestone start. No bot implementation blocks P5A.

## Pricing and product entitlements `[P5C]`

- Decide free/paid plans, pricing, product usage allowances and feature gates with the user.
- FR-RATE-1/2: Enforce the agreed commercial entitlements in code. These supplement P4 operational protection rather than replacing it.
- No advance assignment of core memory, bots or P6 tools to a paid tier. No paid LLM authorization follows from paid user plans. P5C does not block P5A or depend on P5B.

## Independent upgrades `[P6]`

- Resume/cover-letter tailoring and its preparation critic; exact stored statements, on demand for one chosen job.
- Resume curation with source preservation and honest new-layout fallback; interview research with evidence and insufficient-data behavior.
- FR-MCP-1: Approved search/JD/resume-fact/research tools, after permission and authenticated-data-access review.
- Learned scoring/FR-MEM-2: explicit opt-in, cold-start protection, bounded adjustments, revocation and no cross-user learning. Existing prototype stays OFF.
- Each upgrade needs separate requirements, live acceptance and user-reviewed exposure. Preserve current prototype data/tests; do not expose unfinished upgrades or couple the core tracker to their drafts.

## Privacy and release acceptance

FR-PRIV-1/2/3 remain P4: deletion, plain privacy notice and no training without separate opt-in. Core acceptance includes complete owned-data deletion semantics, no raw resume/token/key logs, isolation on direct API calls, real PostgreSQL recovery and measured beta capacity. See `core-release.md` for release gates; P1–P3 fixture history does not waive them.
