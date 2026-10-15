# Phase 3 — Historical Facts, Memory and Evaluation Sequence

The local implementation contains structured facts and saved search snapshots. These do not imply conversational context or production accounts. This list records prototype ownership; see `phase-4-tasks.md` for current release work.

1. Golden dataset runner measuring tool/spec correctness and actual ranking quality, with independent labels.
2. Adversarial hard-filter/soft-preference checks and evaluation documentation. Impossible hard filters yield honest empty results.
3. Stable-source MemoryFact consolidation from exact resume facts and explicit tracker outcomes, with replacement/correction/deletion behavior.
4. Historical consent-gated learned-scoring experiment — code/evidence retained, release deferred to P6 and OFF by default.
5. Historical learned-weight recalibration/math documentation — P6 upgrade reference, not conversational memory.
6. Historical optional scoring integration — core production must hide controls and deny activation until separately accepted.
7. Existing outcome-based fixture comparisons establish their recorded prototype scope. They do not certify a live model, coverage, conversational memory or production persistence.

P4 now adds contextual follow-ups, account-owned preferences/history, core UI/tracker hardening, live discovery evidence and Supabase PostgreSQL/Auth. P5A deployment does not depend on learned scoring, MCP, bots or pricing.
