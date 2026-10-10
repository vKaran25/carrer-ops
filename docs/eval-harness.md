# Scoring evaluation

The Phase 3 runner checks tool-call validity, hard/soft extraction accuracy and ranking quality against a fixed fictional golden dataset. The production adapter app.scoring:rank_for_eval receives only specs, jobs, profile and a fixed date, never labels. It ignores scalar fixture signals used by the synthetic mock scorer.

## Modes

```sh
# Replayed parser, actual local embeddings and Layer 1 ranking
.venv/bin/python tests/eval_harness.py --offline-engine --min-ndcg 0.8
# Actual free OpenRouter parser + actual local engine after configuring .env
.venv/bin/python tests/eval_harness.py --min-ndcg 0.8 --persist
# Runner smoke test, replayed parser and synthetic scalar scorer
.venv/bin/python tests/eval_harness.py --mock
```

--case ID selects one case; --dataset path.json supplies a dataset; --mock-outputs supplies separately authored replay responses; --scorer module:function supplies a sync/async real adapter. Missing live configuration/adapters fail without synthetic fallback. --persist saves per-case NDCG and notes in the local EvalRun table.

## Metrics

- Tool validity requires one correctly named result accepted by the production parser, including schema/evidence checks.
- Hard/soft accuracy compares normalized list/factor sets, targets and weights with independent labels. Alternative exact evidence quotes are allowed.
- P@k divides labeled hits in the top k by k; missing slots are misses.
- R@k divides those hits by all labeled relevant candidates.
- NDCG@k uses descending grades n through 1 from expected order, gain 2^grade - 1 and discount log2(position + 1), normalized against ideal order.

Errors remain in the denominator at zero ranking score; duplicate/unknown returned IDs fail. Exit codes: 0 completed checks/threshold, 1 failed case/spec/threshold, 2 setup error. Default minimum NDCG is zero; set --min-ndcg for a gate.

Recorded offline engine results: five cases, P@2/R@2 0.900, NDCG@2 0.965. Replay tool/spec accuracy is 100%, not a live LLM benchmark. The small fictional set does not represent actual hiring outcomes; labels were not adjusted to match scorer results.

tests/test_scoring.py covers adversarial soft relaxation, impossible hard filters, unknown metadata and Java versus JavaScript. Fixture/user outcome tests separately cover cold start and consent-gated personalized changes.

## Extend the dataset

tests/golden_dataset.json has schema version 1, fixed as_of, positive top_k, fictional profile, unique job_id candidates and unique cases with queries, expected specs and ordered expected IDs. Label cases independently from profile and descriptions. Write offline responses separately in tests/eval_mock_parser_outputs.json; never generate predictions from labels.
