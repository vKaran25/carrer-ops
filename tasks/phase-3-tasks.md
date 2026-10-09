# Phase 3 Task List — Memory, Personalization, and Evaluation

Work through these in order, using the same discipline as Phases 1 & 2: check each against its spec file's acceptance criteria before moving to the next. Do not batch multiple tasks into one prompt.

1. **Evaluation harness, Core scoring** — create a static "golden dataset" runner to programmatically evaluate tool-call correctness and ranking quality using a JSON file of benchmark queries. *Spec: docs/full-srs.md (FR-EVAL-1)*
2. **Evaluation harness, Adversarial testing & Documentation** — write specific tests to prove the "relax soft preferences, never hard filters" behavior. Add `docs/eval-harness.md` explaining how to run these tests and add new ones. *Spec: docs/full-srs.md (FR-EVAL-2)*
3. **Memory layer, Schema & Fact Extraction** — create database models for `MemoryFact` and `ScoringWeights`. Implement the logic to extract and consolidate facts from the user's resume and logged tracker outcomes. *Spec: spec/data-models.md & docs/full-srs.md (FR-MEM-1)*
4. **Self-improving scoring (Layer 2), Core Logic** — implement the personalized weighted-adjustment model. It must learn which structured signals correlate with a specific user's positive outcomes. Must include the cold-start safeguard. *Spec: docs/full-srs.md (§6, FR-MEM-2)*
5. **Self-improving scoring (Layer 2), Trigger & Documentation** — implement the scheduled/on-demand trigger to recalculate weights. Add `docs/memory-and-personalization.md` explaining the weight-update math and database triggers. *Spec: docs/full-srs.md (§6)*
6. **Wire Layer 2 into Ranking Engine** — integrate the personalized weights into the existing Layer 1 scoring pipeline (from Phase 2) so that future searches for that specific user apply their historical nudges. 
7. **End-to-end Phase 3 test** — run the evaluation harness against a simulated user with >5 positive outcomes. Prove that Layer 2 successfully adjusts their job ranking compared to a brand-new user making the exact same query.

Phase 4 (MCP server, Multi-platform clients, Monetization) begins only after all 7 pass for real.