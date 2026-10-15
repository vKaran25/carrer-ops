# Core orchestrator, intake and explicit action gate

## Routing `[P1 foundation / P4 readiness]`

- FR-ORCH-1: Route core resume/context, query, discovery, relevance and tracker actions through one backend. Only the orchestrator action gate records Applied.
- Centralized release feature availability must govern both UI and API. Preparation/research/MCP/learned scoring release in P6; existing prototype nodes remain dormant in the core production profile.
- Acceptance: upload → search → contextual follow-up → inspect JD → Interested → explicit Applied → manual stages works without a preparation node. Direct API requests cannot invoke deferred features.

## Getting started `[P1–P3 foundation / P4 hardening]`

- FR-START-1: The core search requires a stored resume. Upload valid DOCX inline on Search chat; current filename/remove × reveals Add resume (.docx) after removal. Other formats produce a clear DOCX error.
- FR-START-2: Extract exact stored source statements for ranking; preserve the existing valid resume on failed replacement and clear stale fit information on successful replacement/removal. Do not assess authenticity.
- FR-START-3: Separate structured onboarding remains deferred. Legacy query-only API modes are prototype compatibility, not the core onboarding promise.

## Explicit action gate `[P1 / P4]`

- FR-GATE-1: Applied always requires explicit user action plus a corresponding audit record. It records an external action; it never submits an application.
- Search creates zero applications; Interested is the audited intake action and preserves existing later progress.
- Core Mark as Applied is independent of deferred preparation and stale critic results. A saved/failed prototype draft must not block recording the user's external application.
- Acceptance: reject false-action/generic-status/direct-bypass paths and test concurrency/idempotence on PostgreSQL as well as the local prototype. Preserve historical audits and application progress.

Owning production identity, operational and memory requirements: `core-release.md`. Discuss unselected session and execution architecture before implementing.
