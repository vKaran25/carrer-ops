# Query understanding and content relevance `[P2 / P4; learned scoring P6]`

## Confirmed core workflow

The main search requires stored exact DOCX resume facts. A blank optional query ranks eligible discovered jobs against the resume. A specific query adds evidenced filters/preferences while resume fit remains the baseline. Local embeddings are approved; all generative calls use free, tool-capable OpenRouter models.

Resume statements are source truth without authenticity assessment. Do not turn every resume skill into a mandatory filter or require every JD qualification before displaying a relevant job. Keep weak eligible matches visible.

## Query contract

- FR-QUERY-1: Produce a validated query spec with hard fields (recency, technologies, roles, companies, industries, locations) and evidenced soft preferences (e.g. seniority, domain relevance, supported company-tier preference).
- FR-QUERY-2: Hard filters never relax; soft preferences affect rank, not eligibility. Unknown metadata does not establish a match. Do not infer company size, response probability or prior employers from absent evidence.
- Test distinct specs for recent resume-based jobs, junior/company-tier preference, project-domain similarity, Java backend/fintech and explicitly grounded prior-employer queries.
- P4 geography: approved offline GeoNames aliases/coordinates, with ambiguity clarification. Nearby defaults to a visible 50 km preference; farther jobs may appear within the anchor country. Overall fit uses 80% existing relevance plus 20% location credit (1 inside, radius/distance outside, 0 unknown distance). Country evidence remains mandatory; explicit radius boundaries remain strict. Plain city requirements do not broaden. Nearby implementation and remaining strict-city acceptance: `../docs/geography-and-fit.md`.

## Contextual follow-ups `[P4]`

The P4 local context layer now supplements saved search snapshots; see `../docs/search-context.md` for implemented behavior and pending live/account acceptance. The target must resolve “same role, but in Delhi” against the last successful intent, respect explicit new overrides, and start a new intent for unrelated standalone queries. Store only explicitly saved preferences as durable choices, visibly applied and editable/removable. Clarify ambiguous references; failed runs do not silently change context. Reset preserves history/resume; resume changes invalidate outdated match evidence. Full ownership and acceptance: `core-release.md`, FR-CTX-1–4.

## Content relevance `[P2 / P4]`

- FR-RANK-1: Score eligible source-backed JDs using semantic similarity plus supported query signals.
- FR-RANK-2: Return weaker eligible matches when available. If the mandatory-filter pool is empty, return an honest explanation of coverage and exclusions; never manufacture jobs or relax required constraints.
- FR-RANK-3: Explain fit using actual resume/query/JD evidence. Scores are content relevance, not empirical hiring probabilities.
- Clicking a score opens an inline breakdown in the existing job card: actual component values/weights/points, exact input/query evidence, location distance/radius and unknowns. Do not invent per-skill point attribution for semantic embeddings. Saved chat snapshots retain the breakdown; stale resume scores/details must be hidden.
- Clear stale scores after resume replacement/removal while preserving historical descriptions and tracker progress.

## Learned adjustment `[P6]`

The consent-gated prototype historically built under P3 is deferred from the core release and stays OFF. Retain its implementation/test evidence, but hide controls and deny activation in the production core profile. A future P6 release needs explicit opt-in, enough real user-logged outcomes, bounded per-user adjustments, revocation/deletion and separate acceptance. See `../docs/memory-and-personalization.md` for prototype math; do not treat that math as conversational memory.

## Acceptance

Verify labelled parser specs, exact evidence, strict filters, weaker soft matches, honest mandatory-empty results, ambiguous/override/reset follow-ups, stale resume evidence and per-user context isolation. Validate general Indian/international geography. Fixture parser success does not certify the live free model; live coverage/relevance gates and numerical threshold review belong to P4.
