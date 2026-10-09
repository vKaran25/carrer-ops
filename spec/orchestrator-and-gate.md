# Orchestrator, Getting Started, and the Human Approval Gate

## Orchestrator `[P1]`
- FR-ORCH-1: LangGraph supervisor routes to the correct module (scout, tailor, critic, interview research, tracker). Only the orchestrator invokes the human approval gate — no other module may.
- *Acceptance*: a full run (search → tailor → critique → approve) completes through the graph without manual agent invocation.

## Getting Started `[P1]`
- FR-START-1: Resume upload is optional, not required, to perform a search. A user can go straight to a natural-language query with no resume on file.
- FR-START-2: If a resume is uploaded, extract structured facts (skills, roles, education, experience) for use in tailoring and scoring.
- FR-START-3: A structured onboarding profile form is explicitly **not** built now — deferred pending separate evaluation. Don't build one speculatively.

## Human Approval Gate `[P1]`
- FR-GATE-1: No application may become "applied" without explicit user action. This is a permanent design decision — it holds even if autoapply becomes technically trivial later. See `AGENTS.md` non-negotiable rules.
- *Acceptance*: no code path exists that sets an application's status to "applied" without a corresponding logged user action.

## Why this matters (context, not a requirement)
Every autoapply-at-scale competitor researched showed hallucination, ATS spam-flagging, or fraud-adjacent reviews tied directly to removing the human from the loop (see `/docs/competitive-analysis.md`). This gate is the single most evidence-backed decision in the whole system — treat it as load-bearing, not optional scaffolding.
