# Data Models

| Entity | Key fields | Notes |
|---|---|---|
| User | id, email, auth_provider, tier (free/paid), created_at | `[P1]` can be a single local user row; multi-user auth is `[P4]` |
| ResumeProfile | user_id, raw_resume_text, latex_source (nullable), structured_facts (json) | `latex_source` present only if user supplied `.tex` |
| JobPosting | id, user_id, title, company, location, url, snippet, source (ats/bs4/playwright), found_at | scout agent output |
| Application | job_id, status, tailored_resume, tailored_cover_letter, fit_score, explanation, applied_at, outcome | `explanation` is the grounded per-job reasoning text (P2) |
| InterviewResearchCache | company (unique), rounds (json incl. example question types), difficulty_note, researched_at | `[P2]`, shared across all users |
| MemoryFact | user_id, fact_text, fact_type, source, updated_at | `[P3]` |
| ScoringWeights | user_id, weights (json), last_recalibrated_at, outcome_count | `[P3]` — personalized Layer 2 adjustment |
| EvalRun | id, timestamp, test_case_id, score, notes | `[P3]` |

Build only the `[P1]`-relevant fields of `User`, `ResumeProfile`, `JobPosting`, and `Application` now; add the rest as their owning phase begins.
