# Career Ops Copilot — Agent Instructions

## What this is
A multi-agent job-search system: LangGraph orchestration, FastAPI backend, SvelteKit frontend, OpenRouter for all LLM calls. Full specs live in /spec — one file per module. Read only the file(s) relevant to your current task, never the whole folder at once.

## Current authorized scope: P1 through P3
The user requested completion and testing through Phase 3. The existing checkout contains a backend scaffold and query parser, but lacks the Phase 1 core loop. Restore the Phase 1 prerequisites, implement Phase 2, then complete Phase 3. Check the owning acceptance criteria before marking any phase done. Phase 4 and Phase 5 remain out of scope. Ask the user for UI decisions before implementing the UI structure.

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
Backend: `.venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000`
Backend tests: `.venv/bin/python -m pytest -q`
Frontend: `npm --prefix frontend run dev`
Frontend checks: `npm --prefix frontend run check`, `npm --prefix frontend run build`, `npm --prefix frontend test`
Acceptance results and live test commands: `docs/implementation-status.md`, `README.md`

## Confirmed user decisions
Light blue workspace with Search chat, Job tracker, Settings. One continuous locally saved chat, resume controls beside its composer (current filename with remove ×, then Add resume (.docx); new uploads are DOCX only for now), resume-based default search with an optional specific query. Search results stay in chat with collapsible JD/fit cards; explicit Interested adds a job to the tracker. Preparation actions live only in the tracker. Legacy Found jobs move to Interested at the user's request; preserve later stages. Kanban with list toggle and confirmed × removal from Interested that preserves chat/audit history. Worldwide tech jobs from configured public sources. Local embeddings. Uploaded resume statements are the source of truth; do not assess their authenticity. Match by resume relevance without requiring every JD requirement; explicit user filters remain strict and weak soft matches remain visible. Exact stored statements only for tailoring/curation. Preserve LaTeX layout with an advisory for columns/tables. Only free OpenRouter models. Fictional fixtures are allowed in isolated tests. Local outcome-based model learning remains OFF at the user's request. Use recommended choices for further routine decisions without asking again.

## Before marking any task done
Check it against the acceptance criteria listed in its spec file, not just "it runs."

## Approved discovery integration
Query-driven web discovery supplements configured public boards; current provider is optional Tavily with bounded basic-search calls. Search on LinkedIn prepares a dynamic external search; the user browses there. Import LinkedIn job stays inline in Search chat and accepts a specific URL plus pasted JD/title/company, with optional location. Availability is explicitly unverified. No LinkedIn login, scraping or automated application. Unretrieved web leads show links without invented scores. Only Interested creates a tracker application, and reimports preserve existing progress.
