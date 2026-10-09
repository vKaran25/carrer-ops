# Phase 1 Task List — Ordered, Dependency-Based

Work through these in order. Each depends on the one(s) before it. Check each against its spec file's acceptance criteria before moving on — don't just confirm "it runs."

1. **Project scaffold** — repo structure, FastAPI backend skeleton, SvelteKit frontend skeleton, OpenRouter credentials wired into config (no agent logic yet, just confirm the stack boots). *Spec: architecture.md*
2. **Data models** — `User` (single local row is fine for now), `ResumeProfile`, `JobPosting`, `Application` tables via SQLModel. *Spec: data-models.md*
3. **Orchestrator skeleton** — one LangGraph graph, one node, returns a hardcoded response. Confirms the graph runs end to end before any real agent logic exists. *Spec: orchestrator-and-gate.md*
4. **Getting-started flow** — resume upload (optional) or direct query entry, no structured form. If a resume is uploaded, extract structured facts into `ResumeProfile`. *Spec: orchestrator-and-gate.md*
5. **Scout agent (BS4 path only)** — implement `search_jobs`, reusing the builder's existing BS4 crawler for crawl/queue/dedupe logic. Save results into `JobPosting`. ATS/Playwright paths are P2 — don't build them yet, but keep the function signature stable. *Spec: scout-agent.md*
6. **Tailor agent** — on-demand, single-job trigger; drafts resume bullets/cover letter from a JD + stored profile facts. *Spec: tailor-and-critic.md*
7. **Critic agent** — fact-checks tailor output against stored profile; flags unverifiable claims. *Spec: tailor-and-critic.md*
8. **Human approval gate** — wire the orchestrator so only an explicit user action can set `Application.status` to "applied." No other code path may do this. *Spec: orchestrator-and-gate.md*
9. **Tracker/dashboard** — pipeline view (found/tailored/applied/interviewing/resolved), manual status updates. *Spec: tracker-ux.md*
10. **End-to-end test** — one real job: found → tailored → critic-checked → approved → tracked. This confirms the whole P1 loop actually works before moving to P2.

P2 begins only after all 10 are done and the end-to-end test passes for real, not hypothetically.
