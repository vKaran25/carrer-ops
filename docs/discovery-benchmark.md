# P4 discovery benchmark

The user approved the initial gates on 15 October 2026. This is separate from fixture regression tests and full P4 acceptance. Live execution waits for the user's notification that TAVILY_API_KEY has been added; no personal resume is used and the capture tool never opens the workspace database.

## Fixed cases and gates

Cases live in `../tests/discovery_benchmark.json`: 8 Indian cases (Delhi area, Bengaluru, Pune, Hyderabad, Chennai, Kolkata, Ahmedabad and Kochi) and 4 international cases (London, Berlin, Singapore, Toronto), spanning backend/frontend/data/QA/DevOps and junior/general roles. Each uses independently authored fictional skill/project facts.

- Zero mandatory-filter violations or fabricated/source-unsupported evidence.
- At least 70% relevance among returned scored results in the reviewed top 10, pooled across the batch. Fit scores are not review labels. Sparse coverage is assessed separately.
- At least 3 relevant, source-backed, eligible jobs in 6 of 8 Indian cases with independently verified eligible openings.
- At least 5 distinct verified Indian employers outside the configured seed list across the batch. Unknown employer size cannot be counted as evidence of a small company.

The benchmark does not automatically pass international coverage or certify P4 security/persistence/UI. Record international gaps, duplicates, link validity, source description availability, freshness and real provider-credit consumption for review.

## Capture after keys are ready

Run from the repository root, choosing a new output path each time:

```powershell
.venv/Scripts/python.exe tests/discovery_benchmark.py --capture --output tmp/discovery-review-20261015.json
```

This explicitly uses real OpenRouter parsing, Tavily, employer-page retrieval and local ranking. It uses the checked-in default seed sources and an empty tracked-URL set, so workspace history cannot distort coverage. Defaults allow up to 3 web-query attempts per case (36 across 12), but actual requests depend on configured limits/cache. Query attempts are not charged-credit measurements; record the provider dashboard before/after. No automatic paid fallback.

## Independent review

Inspect each case's original query, parsed filters, retrieved JDs, source links and known dates. Mark `effective_filters_reviewed` true only when the parsed intent matches the user's query. Review mandatory constraints against the original query, not merely against what the parser happened to emit.

For every returned job, complete `review.relevant`, `mandatory_filters_satisfied`, `source_evidence_supported`, `verified_employer_name` and notes from source evidence. Independent relevance labels must not be inferred from fit scores. For Indian cases, establish eligible-opening availability independently, record actual public reference-opening URLs, and set `eligible_openings_verified`; do not build references solely from jobs the app already returned. Keep missing/unverifiable evidence pending. Do not invent vacancies to fill a benchmark slot.

```powershell
.venv/Scripts/python.exe tests/discovery_benchmark.py --review tmp/discovery-review-20261015.json
```

Review mode has no network calls. Unreviewed cases/results cannot pass; duplicates cannot inflate coverage, and any source/mandatory-filter failure fails the gate. Exit codes: 0 passed/completed capture, 1 failed or pending review / case capture failures, 2 setup/schema errors. A completed capture still requires independent review.

## Current status

Live capture was executed after the user's key-ready notification on 15 October. See [the test report](testing-2026-10-15.md): seven scored Indian results total, zero Indian cases reaching three, and three international GeographyError failures. The approved coverage target cannot pass from this capture. Independent relevance/source labels, reference-opening review and actual charged credits remain pending. The paragraph below records the pre-run implementation state.

The 12-case definition, capture/review command, isolated evaluator regressions and nearby geography/scoring increment are implemented. Live capture, independent references, relevance/source labels and real credit measurements are pending the user's Tavily-ready notification. General strict-city alias/ambiguity acceptance also remains open. Do not report fixture results as live coverage.
