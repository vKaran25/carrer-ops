# Phase 1 — Historical Prototype Foundation Sequence

This records the original implementation sequence, not a claim that every live acceptance passed. The 15 October 2026 roadmap supersedes old resume-optional/Found and preparation-dependent release gates. Current core implementation follows `phase-4-tasks.md` and `../spec/core-release.md`; tailoring/critic release belongs to P6.

1. FastAPI/SvelteKit/OpenRouter scaffold and configuration.
2. Local SQLModel user, resume, job and application entities.
3. Initial LangGraph routing scaffold, followed by real discovery wiring.
4. Resume intake/source facts. Current confirmed core intake requires DOCX; optional-resume onboarding was superseded.
5. Initial static discovery, followed by later ATS adapters; save descriptions separately from application intake.
6. Historical on-demand tailoring experiment — retain code/evidence; release validation moved to P6.
7. Historical preparation critic experiment — retain code/evidence; release validation moved to P6.
8. Explicit Applied action and persistent audit, permanent across later phases.
9. Tracker foundations. Current target is Interested → Applied → Interviewing → Resolved; legacy Found/Tailored are migration history.
10. Historical search/preparation/gate experiment. The new core end-to-end gate is upload → search → follow-up → explicit Interested → explicit Applied/manual tracking, without preparation.

See `../docs/implementation-status.md` for actual passes and pending live limitations. P6 completion is not required before P4/P5A.
