# Tailor & Critic Agents `[P1]`

## Tailor Agent
- FR-TAILOR-1: Drafts resume bullets/cover letter **only on user demand, per single job** — never automatically across all scouted results. See `AGENTS.md` non-negotiable rules.
- FR-TAILOR-2: Output is always a draft; never changes application status.

## Critic Agent
- FR-CRITIC-1: Fact-check tailor/curator output against the user's stored profile; flag any claim not traceable to stored facts.
- FR-CRITIC-2: Contribute to the fit-score's content-based layer (see `query-and-scoring.md`).

## Acceptance
Two different JDs for the same user produce visibly different tailored output, both grounded in the user's actual stored experience. A deliberately planted fabrication in a test draft is caught and flagged before reaching the human approval gate.

## Why the critic agent is non-negotiable (context)
This directly answers the most-cited specific complaint against the closest competitor (Jobright) — resume/cover-letter hallucination, "confident fiction" about experience the candidate doesn't have. See `/docs/competitive-analysis.md`.
