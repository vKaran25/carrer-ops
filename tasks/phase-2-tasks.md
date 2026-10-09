# Phase 2 Task List — Ordered, Dependency-Based

Work through these in order, same discipline as Phase 1: check each against its spec file's acceptance criteria before moving to the next, don't batch multiple tasks into one prompt.

1. **Query parser** — one LLM call converting a natural-language query into a structured `query_spec` (hard filters + soft preferences). Test against the five example queries in the spec before moving on. *Spec: query-and-scoring.md*
2. **Confidence scoring, Layer 1** — content-based fit-score (semantic similarity + query_spec soft-preference signal boosts). No personalization yet — that's Layer 2, Phase 3. *Spec: query-and-scoring.md*
3. **Wire query parser + scoring into the search flow** — replace Phase 1's placeholder keyword search with the real query_spec → scout → rank pipeline. Confirm: an over-specific query still returns a non-empty, honestly-lower-confidence ranked list, not an empty result. *Spec: query-and-scoring.md*
4. **ATS-aware scout upgrade** — add the `known_ats` lookup (Greenhouse/Lever/Workday JSON APIs) inside the existing `search_jobs` function, without changing its external contract. BS4 remains the fallback for non-ATS static pages. *Spec: scout-agent.md, FR-SCOUT-2*
5. **Playwright fallback** — only for JS-heavy career sites where neither the ATS API nor BS4 returns usable data. Log these cases rather than silently failing. *Spec: scout-agent.md*
6. **Resume curator, LaTeX path** — statement-level parsing of a `.tex` source into addressable, ID-tagged statements; splice-editing grounded in stored profile facts only. Test: two different JDs against the same `.tex` resume produce identical formatting outside the edited bullets. *Spec: resume-curator.md*
7. **Resume curator, PDF/Word fallback** — clean pre-built ATS-friendly LaTeX template for non-`.tex` uploads, honestly labeled as a new layout, not a preservation of the original. *Spec: resume-curator.md*
8. **Interview research agent** — fixed query templates, fetch/aggregate top results, single synthesis call, shared cache keyed by company (~60-day freshness), on-demand trigger only. Test on a well-documented company and a deliberately obscure one — the obscure one must return "insufficient information," never a fabricated structure. *Spec: interview-research.md*
9. **Wire resume curator + interview research into the UI** — "Curate resume" and "Research this company" actions on the job detail view.
10. **End-to-end Phase 2 test** — run one of the five complex example queries from end to end: ranked results with explanations → curate a resume for one result (`.tex` path) → research that company's interview structure. All three must work together before calling Phase 2 done.

Phase 3 (memory layer, personalized scoring Layer 2, evaluation harness) begins only after all 10 pass for real.
