# Data responsibilities and phase ownership

This is a semantic requirements map, not a completed schema migration. Existing SQLModel entities remain prototype evidence. Exact new schemas/identity mapping and execution mechanisms are discussed with the user before implementing them.

| Entity / responsibility | Core and phase requirements |
|---|---|
| User / authenticated identity | Existing local row; P4 maps verified Supabase identity to owned data and server-enforced invitation eligibility. Public admission later reuses that model. Pricing/tier decisions belong to P5C. |
| ResumeProfile | Owned exact DOCX facts/source spans and resume version/hash; failed replacement preserves the prior profile. Private access and deletion in P4. LaTeX curation source is dormant P6 data. |
| JobPosting | Owned title/company/location/URL/description and provenance, source identifiers, known dates and retrieval state; distinct requisitions remain distinct. No invented metadata. |
| Application | Created only after Interested. P4 stages: interested/applied/interviewing/resolved. Applied needs an explicit audited action. Retain outcomes and dormant draft/critique/curated fields without exposing upgrades. |
| UserAction | Durable ownership-scoped intake, status/removal/restore and migration audit. Preserve the Applied invariant on PostgreSQL, including concurrency. |
| ChatTurn | Persist query/results and resume version independently of applications; current snapshots alone are not contextual memory. P4 requires ownership and scalable history access. |
| Search context / explicit preferences (planned P4) | Separate active successful intent, explicitly saved preferences and exact resume facts. Visible overrides/edit/remove/reset; invalidate stale resume evidence; no inferred qualifications. |
| Search execution state (planned P4) | Support durable status, partial/failure diagnosis, refresh/reconnect and idempotent retry without duplicate turns/applications. Exact worker/schema design is a decision checkpoint. |
| MemoryFact | P3 source-identified resume/outcome facts with add/update/delete; no learning implied. P4 isolation/deletion. |
| EvalRun | Evaluation evidence with clear fixture/live modes and no private cross-user leakage. |
| InterviewResearchCache | Dormant P6 public-company research cache; never mix private resume/context data into shared content. |
| ScoringWeights / PersonalizationConsent | Existing P3 prototype deferred to P6. OFF; no activation in the core production profile. Explicit future consent/revocation and isolation remain mandatory. |

## Persistence and compatibility

- Current SQLite/hardcoded local user is not production account support. P4 uses Supabase PostgreSQL/Auth starting free, versioned migrations and real PostgreSQL acceptance.
- Start beta accounts empty; existing local data stays intact. Owner import is a separately reviewed operation, never an automatic first-login assignment.
- Audit Tailored → Interested while preserving artifacts and Applied/later stages. No application is automatically marked Applied by migration.
- Account deletion covers active private data, context/preferences and artifacts. Agree backup retention/deletion semantics before deployment.
- Provider credentials, service-role credentials and global operator configuration are not end-user fields or client-visible data.

Complete acceptance and unselected architecture checkpoints: `core-release.md`.

## 16 October schema implementation (not yet accepted)

The initial frozen Alembic migration is written for an empty private PostgreSQL schema. It includes AuthIdentity (verified UUID → internal user), Invitation, SearchRun, WorkerHeartbeat, DailyUsage, DiscoveryCache (public Tavily response only) and DeletionRequest alongside the owned core/dormant entities. No SQLite records are imported. Account-bound handlers use session ownership rather than client user IDs; Postgres acceptance is deferred until separately authorized.

Deletion removes active owned records immediately; minimal Auth/file cleanup markers remain only until external/local cleanup succeeds. No retained application backups are configured, per the user's 16 October decision. Private fit, resume, chat and tracker records are not shared cache entries.
