# Career Ops Copilot — Agent Instructions

## What this is
A multi-agent job-search system: LangGraph orchestration, FastAPI backend, SvelteKit frontend, OpenRouter for all LLM calls. Full specs live in /spec — one file per module. Read only the file(s) relevant to your current task, never the whole folder at once.

## Current active phase: P2 (query engine + ATS scraping + interview research + resume curator)
Phase 1 is complete and tested. Build only what's tagged `[P2]` in the relevant spec file. `[P3]`/`[P4]` items are fully specified but OUT OF SCOPE right now. Do not build them early, and do not skip a `[P2]` item because a later-phase one looks more interesting.

## Non-negotiable rules — apply at every phase, no exceptions
- No agent may ever mark an application "applied" without an explicit user action. Permanent rule, not a current-phase limitation.
- Resume/cover-letter tailoring happens only on user demand, per single job — never automatically for every scouted result.
- Never fabricate: resume claims, interview questions, or match reasoning not grounded in real stored data. If data is insufficient, say so explicitly rather than inventing a plausible answer.
- Every LLM call goes through OpenRouter; any model used must support tool/function calling.
- User data is never used to train any model without separate, explicit opt-in.

## Where things live
- `/spec/*.md` — requirements per module, each phase-tagged with acceptance criteria
- `/tasks/phase-1-tasks.md` — the ordered, dependency-based build sequence for the current phase
- `/docs/full-srs.md` — complete reference spec (search it for context, don't load it wholesale)
- `/docs/competitive-analysis.md` — why certain decisions were made (reference only)

## Build/test commands
(fill in once the project scaffold exists, e.g. `uvicorn main:app --reload`, `npm run dev`, `pytest`)

## Before marking any task done
Check it against the acceptance criteria listed in its spec file, not just "it runs."
