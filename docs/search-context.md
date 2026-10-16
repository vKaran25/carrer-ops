> 16 October source update: API/worker ownership is bound to authenticated accounts in Supabase mode. Searches now use saved HTTP 202 tickets and a queue; final jobs/chat/context/ticket writes are transactional, with cancellation/retry/recovery guards. History is paged in batches of 25. Source changes are untested; schema activation and separate acceptance are pending. See [operating design](p4-operations.md).

# Structured search memory — P4 increment

Approved on 15 October 2026. This implements contextual search in the local prototype; Supabase authentication, PostgreSQL migrations and production account isolation remain separate P4 work.

## Stored state

- `SearchContext`: per-user explicit intent spec, explicitly cleared fields, last successful query/turn, resume digest and revision.
- `SearchPreferences`: a separately, explicitly saved default query/spec, editable or removable. Saving replaces this user's default set. Ordinary searches, resume uploads and JDs never create permanent preferences.
- `ChatTurn`: historical result snapshots, including the effective query, filters and context decision. Reset does not delete history, resume or saved defaults.

No conversational vector database or training is involved. The classifier sees the current message and prior structured explicit intent, without raw resume/history/JDs. Generative calls still use the free tool-capable OpenRouter gateway and provider privacy/price restrictions.

## Resolution

1. For a nonblank natural-language query, one bounded OpenRouter tool call classifies new intent, follow-up or clarification and identifies explicitly removed fields using exact current-message evidence. A second existing parser call extracts the current message's filters/preferences; no retry or silent keyword fallback.
2. A follow-up retains unchanged explicit fields, overrides newly specified fields and applies evidenced removals. An independent query starts with no previous intent. Ambiguous/no-prior references stop with a clarification before discovery. Unsupported removal evidence fails explicitly.
3. Saved defaults apply first. Explicit intent overrides the same default field. Explicit removals suppress defaults across subsequent follow-ups; defaults can return on a new standalone/empty search or reset. Preferences by factor merge deterministically; changed locations replace conflicting nearby/city scopes.
4. An empty resume search starts a fresh resume/default search, with no inherited previous filters and no context-classifier/parser call. Explicit keyword mode remains a limited separate parser; it also starts fresh.
5. Search completion stores active intent with its chat turn. Parser/model/lookup/ranking exceptions preserve the prior intent. A diagnostic run with no retrieved postings and source warnings preserves it too. A valid, empty mandatory-filter result can still become the active intent.

A conditional revision update prevents an older in-flight run from overwriting a newer search, reset or saved-default edit. A losing run can retain its historical results with an explicit context-preserved notice. This is context protection, not full durable execution/idempotency for search; worker/reconnect handling and real PostgreSQL concurrency acceptance remain pending.

The context spec contains explicit filters/preferences, never inferred resume qualifications or embedded old resume vectors. After a resume change, the panel labels the change and retains explicit filters; all new ranking uses the current resume. Historical fit/breakdown evidence is invalidated separately.

## API and UI

| Endpoint | Behavior |
|---|---|
| `GET /api/search/context` | Active context, saved defaults, visible effective filters and resume-change notice |
| `DELETE /api/search/context` | Start a new intent; preserve history, resume and saved defaults |
| `PUT /api/search/preferences` | Explicitly save/replace `{query: "..."}` after successful parsing |
| `DELETE /api/search/preferences` | Remove the saved default set |

Search chat has a compact **Search memory** accordion with effective filters, **New search**, an editable saved-default field, **Save search preferences** and **Remove saved preferences**. Saving is explicit; typing alone sends no write. Editing defaults does not erase the current explicit intent, which can still override them; New search begins with the updated defaults. User-facing filters and result notices show what was applied. Unsaved preference edits survive background workspace refreshes.

Service helpers take a user ID and fixture tests separate two users. Current HTTP routes still bind the prototype's local user 1. This does **not** establish authenticated cross-account protection or production database acceptance; do not deploy it publicly.

## Evidence and remaining checks

Isolated tests cover follow-up overrides, independent intent, defaults, explicit removals, blank searches, ambiguity, ungrounded evidence, reset, stale revision rejection, preference-edit races, two-user service isolation, failure preservation, resume changes, explicit CRUD and chat retention. Browser fixtures cover explicit save/edit/remove, refresh, reset/history preservation and mobile width. Model responses are fixtures, not live interpretation evidence.

Live free-model follow-ups (including incorrect or ambiguous classification), true authenticated cross-user access, PostgreSQL migration/concurrency, logout/login and deployed recovery remain release gates. New natural-language searches add one context-classification request to existing parser/planning calls; include it in the later approved operation budgets.
