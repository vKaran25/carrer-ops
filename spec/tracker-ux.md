# Tracker / Dashboard `[P1]`

## Requirements
- FR-TRACK-1: Pipeline state per chosen job: interested → tailored → applied → interviewing → resolved
- Confirmed UI decision (11 October 2026): one continuous locally saved search chat. Results remain in chat, with inline collapsible JD/fit details. Only an explicit Interested button creates a tracker entry. Tailor, Curate and Research appear in the tracker after selection. Existing legacy Found entries migrate to Interested at the user's request; later stages retain their data.
- FR-TRACK-2: UX must be easily understandable and trackable at a glance — this is a **mandatory** requirement, not a nice-to-have, per explicit builder direction. Needs dedicated UX research before final screen design — don't lock in a detailed screen design speculatively; research it when this module is actually being built.

- Confirmed UI decision: Interested has a small × with Cancel/Remove confirmation. Removal persists, retains chat/audit history and allows re-selection in chat. Resume controls show the current filename with a small remove ×; only after removal is Add resume (.docx) shown. New uploads accept DOCX only for now, with explicit format errors for other files.

## Acceptance
Status changes persist and reflect correctly across a page reload.
Search must create zero applications or tracker counts; Interested must add one audited entry without duplication or resetting later stages. Chat queries/results survive reload. Resume replacement retains history while clearing stale fit information. Applied still requires the explicit gate.

## Landing page note `[P4]`
When the landing page is eventually built, it should include a pipeline-flow demo (interested → tailored → applied → interviewing → resolved) in the style of modern SaaS product pages, so the product's function is obvious before signup. Not relevant until P4.

## Approved LinkedIn actions — 11 October 2026

Search chat includes Search on LinkedIn (prepare an encoded search, then open it externally) and Import LinkedIn job. Imports use a specific HTTPS LinkedIn job URL plus user-pasted title, company, optional location and full JD. The inline form occupies the scrollable conversation, preserving the composer on desktop/mobile. Imported records are saved chat snapshots, explicitly labeled as user-provided with unverified availability. Interest remains the only tracker intake. Canonical LinkedIn IDs deduplicate reimports without resetting pipeline stages. Unverified web leads are separate links with no score.

Acceptance: prepare query/resume-based external searches without tracker mutations; imports survive refresh; non-job/unsafe URLs and inadequate details are rejected; Interest and Applied gates remain intact; reimport preserves later stages; mobile form/composer remain usable; source warning visible for imported jobs.
