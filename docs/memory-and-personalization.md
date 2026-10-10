# Memory and personalized ranking

Memory facts are consolidated from the current stored resume and explicit tracker outcomes. Each fact has a stable `(user_id, source, source_key)` identity. Replacing a resume removes obsolete facts; correcting an outcome updates its fact instead of appending another record. Facts never invent achievements or outcomes.

Layer 1 uses local semantic similarity and query preference evidence. The user requested local learning remain off. A separate persistent opt-in is required before fitting or applying learned weights; disabling consent deletes those weights. Until both consent and six distinct applications with logged interview, offer, rejection or no-response outcomes exist, ranking uses Layer 1 entirely. Withdrawals are not treated as negative hiring evidence. An application must have the logged Mark as applied action before an outcome can be entered.

Layer 2 fits deterministic batch logistic regression on that user's stored, zero-to-one scoring signals. Interview and offer are positive labels; rejection and no response are negative labels. The fit uses 250 gradient steps, learning rate 0.15, and L2 regularization 0.4. The intercept is trained but not applied to ranking: only relative feature corrections matter. Each coefficient is multiplied by 0.15 and clipped to `[-0.12, 0.12]`. The total per-job adjustment is bounded to 15 score points in either direction. These scores do not predict an empirical hiring probability.

Recalibration runs on demand or after five additional labeled applications. Corrections to existing outcomes are detected by a hash of the training rows; corrected datasets are refit. Cold-start fallback is checked again during every search. One application's interview and eventual offer remain one training record, preventing double counting. No cross-user data is used.

The Resume page exposes consolidated memory and the Settings page exposes calibration status and a Recalibrate action. Tests compare rankings for an experienced fixture user with more than five positive outcomes against a new user making the same query.
