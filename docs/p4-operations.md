# P4 operating design — implementation, not acceptance

Selected 16 October 2026. No deployment or test run was performed in this implementation pass.

## Runtime and schema

Use the standard SvelteKit PKCE/cookie integration, a persistent FastAPI service and Supabase PostgreSQL through its Session pooler. Keep the database/secret API keys only on the backend. The private application schema is `career_ops`; data is not exposed through browser database APIs. See [setup](supabase-setup.md).

The operator applies versioned Alembic migrations explicitly. PostgreSQL startup refuses an unknown schema revision. `ENVIRONMENT=production` refuses local authentication or SQLite. SQLite remains available only for local development; the GeoNames catalog is separate public geography data.

## Search execution

`POST /api/search` now returns HTTP 202 with a persisted ticket; it no longer returns synchronous ranked results. Clients use `/api/search/runs`, `/api/search/runs/{id}`, and explicit `/cancel` or `/retry` actions. Tickets expose query/status/phase/error/turn ID only to their owner.

One worker holds a PostgreSQL session advisory lock globally. One unfinished search is admitted per account. Request keys are scoped to the account and payload; replaying the same key returns the same ticket. A partial unique index also enforces the unfinished-search boundary.

Job records, chat turn, successful context update and ticket completion commit in one transaction. Cancellation and final persistence serialize against the ticket. Changed resume/context while queued requires a new search. Failed/cancelled work does not advance active intent. A worker restart marks abandoned running work interrupted; there is no silent replay of provider calls. Users retry explicitly. Clarification uses `needs_input`, so users edit their query rather than repeatedly retrying an ambiguous place.

Heartbeats support readiness. A ten-minute execution timeout is configurable. Shutdown cancels active execution; the next worker recovers its persisted status. Real restart, cancellation, multi-process and idempotency acceptance is pending.

## Agreed safety caps

| Operation | Default |
|---|---:|
| Search attempts per account / UTC day | 5 |
| Search attempts globally / UTC day | 20 |
| Model call attempts globally / UTC day | 90 |
| Tavily call attempts globally / UTC day | 60 |
| Global search workers | 1 |
| Unfinished searches per account | 1 |

The first four values are environment-configurable. Counters reserve atomically; attempts are counted even if a provider subsequently fails. Provider quotas can stop calls earlier. These are operational protection, not paid/free product allowances. No paid model fallback exists. Standalone operator benchmark tools remain explicit and do not consume workspace counters or open the application database; their provider consumption must be reviewed separately.

## Cache decision

Only public Tavily responses are cached, for ten minutes, using hashed keys and public response fields. PostgreSQL persistence is used for account-bound production calls; the local process cache remains a development optimization. Job descriptions are fetched again, and resume fit, preferences, tracker exclusions and chat state are not shared/cached as search results. Cache hits do not consume another Tavily-call reservation. Counts of attempts/cache hits are diagnostics, not measured charged credits. No employer-posting or private/model-result cache was approved.

## Privacy and deletion

The user selected immediate active deletion **without retained application backups**. Account deletion removes owned resume/profile, chat, context/preferences, tracker/jobs, audit, learned-data records and owned artifacts, and revokes invitation access. Auth deletion is attempted immediately with the backend secret; outages or missing setup leave a minimal retry record. A cleanup worker removes that record after owned files and the remote Auth identity are gone. Provider/infrastructure retention is governed separately by those services; no application backup or restore guarantee is claimed.

This decision supersedes earlier draft seven-day retention/backup-restore gates. Backups may be revisited later only with user discussion. No automatic SQLite import or backup copy is created.

## Diagnostics and incident recovery

- `/health` reports process availability; `/ready` checks DB, geography, model/search configuration, Auth cleanup configuration and a recent worker heartbeat. Configuration presence does not prove provider delivery or model quality.
- API responses are private/no-store. Error logs omit provider payloads, tokens, keys and raw resumes. Worker failures use safe status messages and retain the last successful search context.
- For provider quota failures, inspect the provider dashboard privately, wait for its reset or change approved operating configuration. Do not bypass the free-model policy.
- For a server interruption, restart the same application against the same migrated database. Inspect ticket status and retry failed/interrupted searches explicitly.
- For a bad application release, stop the service and deploy the previous compatible application revision. Do not run destructive schema downgrades; use a reviewed forward repair migration. No deployment or rollback was executed here.
- For a database outage, readiness is false and admissions should stop. With backups intentionally absent, database-loss restoration is not guaranteed. Hosting/monitoring integrations and measured workload/capacity remain pending the separately authorized test and hosting review.
