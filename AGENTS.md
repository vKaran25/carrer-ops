# Career Ops Copilot — Agent Instructions

## What this is
A multi-agent job-search system: LangGraph orchestration, FastAPI backend, SvelteKit frontend, OpenRouter for all LLM calls. Full specs live in /spec — one file per module. Read only the file(s) relevant to your current task, never the whole folder at once.

## Current authorized scope: P4 implementation
After the documentation revision, the user instructed starting P4 implementation, beginning with the baseline audit and discovery hardening. Continue approved work while external setup is pending; new architectural decisions still need discussion. Deployment remains a later P5A action. The checkout contains a local P1–P3 prototype; do not describe it as a missing scaffold or treat prototype tests as production acceptance.

The revised roadmap is P4 core readiness; P5A release hardening/deployment/documentation/demo; P5B Telegram/Discord; P5C pricing, commercial usage allowances and paid feature gates; P6 preparation tools, MCP and optional learned scoring. P5B/P5C do not block P5A. See `spec/core-release.md` and the owning phase tasks before implementing.

The user explicitly requires discussion before new architectural decisions: explain the options, recommend one, and ask. Previously confirmed decisions remain valid; routine edits implementing those decisions do not need another confirmation. Ask before changing UI structure beyond the confirmed release changes.

## Non-negotiable rules — apply at every phase, no exceptions
- No agent may ever mark an application "applied" without an explicit user action. Permanent rule, not a current-phase limitation.
- Resume/cover-letter tailoring happens only on user demand, per single job — never automatically for every scouted result.
- Never fabricate: resume claims, interview questions, or match reasoning not grounded in real stored data. If data is insufficient, say so explicitly rather than inventing a plausible answer.
- Every LLM call goes through OpenRouter; any model used must support tool/function calling.
- User data is never used to train any model without separate, explicit opt-in.

## Where things live
- `/spec/*.md` — requirements per module, each phase-tagged with acceptance criteria
- `/tasks/phase-1-tasks.md` — the ordered, dependency-based build sequence for the current phase
- `/docs/full-srs.md` — complete reference spec (search it for context, don't load it wholesale)
- `/docs/competitive-analysis.md` — why certain decisions were made (reference only)

## Build/test commands
Backend: `.venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000`
Backend tests: `.venv/bin/python -m pytest -q`
Frontend: `npm --prefix frontend run dev`
Frontend checks: `npm --prefix frontend run check`, `npm --prefix frontend run build`, `npm --prefix frontend test`
Acceptance results and live test commands: `docs/implementation-status.md`, `README.md`

## Confirmed user decisions
Light blue workspace with Search chat, Job tracker, Settings. One continuous saved chat, resume controls beside its composer (current filename with remove ×, then Add resume (.docx); new uploads are DOCX only for now), resume-based default search with an optional query. Search results stay in chat with collapsible JD/fit cards; explicit Interested creates a tracker application. Kanban/list toggle and confirmed × removal preserve chat/audit history. The target core tracker is Interested → Applied → Interviewing → Resolved. Preserve legacy records and preparation artifacts; audit Tailored → Interested migration without changing Applied or later progress.

Worldwide tech jobs with India as a mandatory coverage priority. Tavily plus accessible employer sources initially; no JSearch integration in the approved scope. Poor Indian coverage blocks beta pending a reviewed remedy. Core chat gains structured follow-up context and explicitly saved preferences, separate from resume evidence, with visible filters and reset controls. Local embeddings; uploaded resume statements are the source of truth without authenticity assessment. Explicit filters remain strict; weak soft matches remain visible. Only free tool-capable OpenRouter models. Fictional fixtures are allowed in isolated tests.

Approved P4 discovery benchmark: 12 searches (8 Indian / 4 international), zero mandatory-filter or fabricated-evidence failures, at least 70% relevance among reviewed returned top-10 results, at least 3 usable jobs in 6 of 8 independently verified Indian cases, and at least 5 distinct Indian employers outside seed sources across the batch. The user will add Tavily manually and notify when ready; keep live tests separate until then.

Approved location/scoring direction: offline GeoNames aliases/coordinates. “Around/near a city” prefers 50 km by default, adjustable by the user; farther jobs may appear within the anchor city's country with lower location credit and an explicit label. “Within N km only” and other explicit hard constraints remain strict. For an active nearby preference, overall fit is 80% of existing resume/query relevance plus 20% location credit; inside the radius gets full credit, outside gets radius/distance. Clicking a score opens an inline component/evidence/distance/unknown-data breakdown in the job card. Do not invent per-skill numerical contributions from the non-additive semantic similarity model.

First deployment: 10–15 invited testers, clean authenticated workspaces, Google + passwordless email-link login, Supabase PostgreSQL/Auth starting on its free tier. Existing local data stays intact and is not automatically uploaded. Public registration must later use the same account/ownership model. Hosting, SMTP, backup mechanisms, numerical operating limits and new architectural choices require user discussion before implementation. Operational protection belongs in P4; commercial allowances belong in P5C. Deploy the core in P5A without waiting for bots or monetization.

Preparation, interview research, MCP and optional learned scoring are P6 upgrades. Hide deferred UI controls and disable their production API access when implementing the core release; preserve prototype code/data and historical test evidence. Local outcome learning stays OFF. Future preparation uses exact stored statements, on demand per job; preserve LaTeX layout with the approved column/table advisory.

## Before marking any task done
Check it against the acceptance criteria listed in its spec file, not just "it runs."

## Current prototype versus target discovery
The current prototype has optional Tavily and visible manual LinkedIn search/import controls. The revised core prioritizes automatic discovery and will hide those manual buttons initially. Revisit a refined LinkedIn feature with the user if measured coverage requires it; do not add login, scraping or automated application. Current imports are user-pasted, availability-unverified snapshots. Unretrieved web leads stay unscored. Only Interested creates a tracker application, and reimports preserve progress. A documentation change does not itself change this runtime behavior.

Approved P4 structured search memory: separate database records for the last successful explicit intent and explicitly saved default preferences, with a bounded OpenRouter tool classifier for follow-ups/new intents/clarification. Explicit query fields override defaults; failed runs preserve prior intent. Reset keeps history/resume/defaults. Never learn permanent preferences from casual text or JDs. See docs/search-context.md for local implementation and remaining production acceptance.

Approved Supabase session design: standard SvelteKit PKCE/cookie integration with SDK-managed refresh and browser-readable SDK cookies; FastAPI independently verifies signed access tokens and invitation eligibility. Do not silently substitute custom HttpOnly sessions. User has added Supabase URL/publishable-key settings; integration and connection verification remain pending. Setup steps are in docs/supabase-setup.md. Current DATABASE_URL stays local until the production adapter and explicit migration/setup step.

## Decisions confirmed on 16 October 2026

- Complete P4 implementation, but do not run test suites, live queries or personal resumes until the user separately authorizes the test pass. The user will supply DOCX resumes in a folder; `data/test-resumes/` is prepared and ignored by Git. Previous 189/27 test counts are historical and do not validate the new queue/auth/UI source changes.
- Use SQLModel + Alembic + psycopg with Supabase Session pooling. Start an empty PostgreSQL schema; no SQLite data import is wanted. Verified Supabase UUIDs map to internal owned accounts.
- Use an operator CLI database invitation allowlist. The user will add multiple emails; do not create invitations or send messages without supplied addresses/instructions.
- Use a PostgreSQL search queue and one globally leased FastAPI worker; persisted status, cancellation and explicit interrupted/failed retries. Do not silently replay provider calls.
- Operational defaults: 5 search attempts/account/day, 20 global search attempts/day, 90 global model attempts/day, 60 global Tavily attempts/day, UTC resets, one unfinished search/account. Limits are configurable and are not paid plan gates.
- Cache only public Tavily responses for 10 minutes in PostgreSQL; descriptions and private fit/context/tracker results are not cached/shared. Employer-posting caching was not approved.
- Implement Google and email-link flows; configure SMTP later. Resend with a verified domain is the selected setup recommendation. No domain was bought and no mail settings were changed.
- Immediate active account/workspace deletion, without retained application backups, is the current user choice. Retry failed remote Auth/file cleanup with minimal markers. Earlier backup-retention/restore requirements are superseded for this initial scope; revisit only with the user.
- SUPABASE_DATABASE_URL and SUPABASE_SECRET_KEY are being added manually; wait for the user's readiness confirmation before activating the staged PostgreSQL schema. Tests remain separately deferred even after configuration is ready.
