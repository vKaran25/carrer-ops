# Phase 2 — Historical Query, Ranking and ATS Sequence

Historical prototype reference, revised for release ownership on 15 October 2026. Actual evidence remains in `../docs/implementation-status.md`; core hardening follows `phase-4-tasks.md`. Original curation/research tasks are P6 upgrades and do not block core deployment.

1. Natural-language parser with validated hard/soft query specs and independently labelled examples.
2. Local content relevance (Layer 1), grounded in exact resume/query/JD evidence.
3. Wire query → discovery → ranking. Retain weaker soft matches; impossible mandatory filters produce honest empty results. The former unconditional nonempty-result gate is superseded.
4. Add accessible Greenhouse/Lever/Workday ATS adapters inside the core retrieval contract.
5. Add bounded permitted rendered fallback for unsupported JS pages; log failures. P4 must validate its actual deployment resource/access needs.
6. Historical `.tex` curation experiment — P6 release ownership.
7. Historical clean-layout fallback experiment — P6 release ownership; core upload remains DOCX-only.
8. Historical company interview research/cache experiment — P6 release ownership and live evidence still required.
9. Historical preparation controls — remove from the target core UI/API and restore only after P6 acceptance.
10. Core parser/ATS/ranking evidence remains relevant to its scope; the former curation/research completion gate no longer blocks P4/P5A.

The new release must independently validate general geography, Indian/non-seed coverage, contextual follow-ups, account isolation and production persistence.
