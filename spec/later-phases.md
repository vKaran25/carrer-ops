# Later Phases — Fully Specified, Not Yet In Scope

Everything here is `[P3]` or `[P4]`. Read this file only when that phase actually begins — don't build any of it early.

## Memory Layer `[P3]`
- FR-MEM-1: Extract/consolidate facts from resume + logged outcomes (ADD/UPDATE/DELETE, not blind append)
- FR-MEM-2: Store the personalized scoring-adjustment weights (see `query-and-scoring.md`)

## Evaluation Harness `[P3]`
- FR-EVAL-1: Golden dataset scoring tool-call correctness and ranking quality, not just final output
- FR-EVAL-2: Specifically test the "relax soft preferences, never hard filters" behavior against adversarial over-specific queries

## Authentication & Accounts `[P4]`
- FR-AUTH-1: Email/password or Google OAuth
- FR-AUTH-2: Data scoped by `user_id`, never visible across users
- FR-AUTH-3: User can delete their account and all data
- FR-AUTH-4: Tier (free/paid) gates feature access

## Custom MCP Server `[P4]`
- FR-MCP-1: Expose `search_jobs`, `parse_job_description`, `get_user_resume_facts`, `research_interview_structure` as MCP tools

## Multi-Platform Clients `[P4]`
- FR-BOT-1: Telegram/Discord clients call the same orchestrator/scoring path as web — no separate reimplementation (see architecture.md)

## Rate Limiting & Monetization `[P4]`
- FR-RATE-1: Per-user daily cap on LLM-backed actions, enforced in code, not prompt instruction
- FR-RATE-2: Separate pay-gated cap/feature-lock for paid-only features

Freemium split (starting proposal):
| Tier | Includes |
|---|---|
| Free | Resume-based + simple NL search, basic scoring, basic tracker, capped daily complex queries, short-window memory |
| Paid | Higher/uncapped complex queries, resume curation, full interview research, full memory + personalized scoring, Telegram/Discord |

## Privacy & Data Handling `[P4]`
- FR-PRIV-1: User-triggered data deletion
- FR-PRIV-2: Plain-language privacy notice at signup
- FR-PRIV-3: User data is never used to train any model, under any tier, without separate explicit opt-in

## Remaining Non-Functional Requirements
- **Performance**: simple actions feel fast (seconds); complex queries reasonably take a few minutes — accepted tradeoff
- **Scalability/cost**: per-user rate limits + tier gating are the primary controls; shared interview-research cache is the primary cost control for that feature
- **Security**: per-user data isolation mandatory; encrypted storage, user-triggered deletion, plain privacy notice — basic hygiene, not enterprise compliance certification
