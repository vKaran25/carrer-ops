# Query Understanding & Confidence Scoring `[P2, personalization P3]`

Not needed for P1 (P1 can use simple keyword/filter search as a placeholder). Build this when P2 begins.

## Example queries this must handle
- "find me jobs acc to my resume that is posted within this week"
- "find me jobs posted within a week or two that are not high-level companies, since as an intern I have a higher chance at mid-to-low-level companies"
- "find me jobs that best suit my stack of projects — e.g. if I built something similar to what a company builds, my interest and eligibility align better"
- "find me java backend jobs specifically from fintech companies"
- "find me jobs from companies already in my resume where I have a better chance of progressing career-wise"

## Query parsing

### Confirmed search workflow (11 October 2026)
Resume upload and fact review live on Search jobs, with no separate resume navigation page. The main search requires stored resume facts. An empty optional query searches configured public sources and ranks their postings by local similarity to those facts, without an LLM parsing call. A specific query adds its evidenced hard filters and soft preferences; resume fit remains the baseline ranking signal. The uploaded resume is the source of truth; intake/search must not judge the authenticity of user-written qualifications. Matching uses relevance to its roles and skills and does not require the resume to satisfy every JD requirement. Resume skills must not all become mandatory filters. Lower matches remain visible. The legacy keyword/natural API modes remain available.

Workflow acceptance: upload without leaving Search jobs; search with a blank query; narrow with a specific query while retaining resume scoring; reject resume search before intake succeeds; clear stale search results after replacement/removal; retain the current profile when replacement fails.
One LLM call converts the query into a structured `query_spec`: **hard filters** (recency window, explicit tech-stack keywords, explicit company name) and **soft preferences** (company-tier/seniority preference, project-domain similarity, career-fit framing). Hard filters apply as real filters; soft preferences become weighted scoring factors — **never** a hard cutoff. This is what prevents empty results from an over-specific query.

Explicit nearby Delhi queries (around/near Delhi) use a Delhi NCR location requirement. Delhi-only queries remain city-specific; Gurgaon/Gurugram are equivalent city labels. Unknown locations and unrelated cities never satisfy the requirement. Empty search responses explain the recorded location/filter/source result and show checked coverage and source warnings.

## Scoring (Layer 1, content-based — P2, day-one usable)
Every candidate gets a fit-score from: (1) semantic similarity between JD and resume/profile facts, (2) structured signal boosts/penalties from the query_spec's soft preferences.

## Scoring (Layer 2, personalized — P3)
As a user logs real outcomes (applied → interview → offer/reject/no-response), a lightweight per-user weighted-adjustment model learns which structured signals correlate with *that user's* positive outcomes. **Do not use matrix factorization / collaborative filtering / Bayesian personalized ranking** — those need population-scale cross-user data this product won't have; using them here is a technique/data-regime mismatch, not sophistication (see `/docs/competitive-analysis.md`). Recalibrate on a scheduled/on-demand basis (e.g. every N new outcomes), not continuous live gradient updates. Cold start: fall back entirely to Layer 1 until ~5-10 logged outcomes exist.

## Requirements
- FR-QUERY-1/2: parse into hard+soft; hard filters never relaxed, soft preferences always can be
- FR-RANK-1/2/3: every candidate scored; always return a ranked list (relax soft preferences, never hard filters, rather than return empty); every result carries a grounded explanation referencing the specific query_spec factors that drove it — never a vague blurb

## Acceptance
The five example queries above each produce a distinct, correctly-structured query_spec. An intentionally over-specific query still returns a non-empty, honestly-lower-confidence ranked list with a stated relaxation note.
