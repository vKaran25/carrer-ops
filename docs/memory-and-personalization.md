Current P4 update: the approved structured search-context/default-preference layer is now implemented locally. See [search context](search-context.md) for persistence, overrides/reset, API and pending production/live acceptance. The outcome-learning prototype below remains OFF and deferred to P6.

# Structured facts, conversational memory and deferred learned ranking

## Release ownership — 15 October 2026

Current runtime: exact structured facts and saved ChatTurn query/result history. New searches do not currently use previous messages as context. P4 adds authenticated active search intent and explicitly saved preferences, with follow-up overrides, ambiguity handling, visible filters, edit/remove/reset and stale-resume invalidation. See [core context requirements](../spec/core-release.md).

Outcome-based learned ranking below is a historical P3 prototype, now a **P6 upgrade**. It stays OFF. Its existing Settings controls will be hidden and activation denied in the core production profile when P4 is implemented. Outcome records can remain without training. Core deployment does not depend on this prototype or a quota of outcomes.

## Existing fact consolidation

Memory facts are consolidated from the current stored resume and explicit tracker outcomes. Each fact has a stable `(user_id, source, source_key)` identity. Replacing a resume removes obsolete facts; correcting an outcome updates its fact instead of appending another record. Facts never invent achievements or outcomes.

## Dormant learned-scoring prototype — P6 release

Layer 1 uses local semantic similarity and query preference evidence. The user requested local learning remain off. A separate persistent opt-in is required before fitting or applying learned weights; disabling consent deletes those weights. Until both consent and six distinct applications with logged interview, offer, rejection or no-response outcomes exist, ranking uses Layer 1 entirely. Withdrawals are not treated as negative hiring evidence. An application must have the logged Mark as applied action before an outcome can be entered.

Layer 2 fits deterministic batch logistic regression on that user's stored, zero-to-one scoring signals. Interview and offer are positive labels; rejection and no response are negative labels. The fit uses 250 gradient steps, learning rate 0.15, and L2 regularization 0.4. The intercept is trained but not applied to ranking: only relative feature corrections matter. Each coefficient is multiplied by 0.15 and clipped to `[-0.12, 0.12]`. The total per-job adjustment is bounded to 15 score points in either direction. These scores do not predict an empirical hiring probability.

Recalibration runs on demand or after five additional labeled applications. Corrections to existing outcomes are detected by a hash of the training rows; corrected datasets are refit. Cold-start fallback is checked again during every search. One application's interview and eventual offer remain one training record, preventing double counting. No cross-user data is used.

The local API exposes consolidated facts; the prototype Settings page exposes calibration and Recalibrate controls. These learning controls are deferred from the target core UI; there is no separate core Resume navigation page. Tests compare rankings for an experienced fixture user with more than five positive outcomes against a new user making the same query.
