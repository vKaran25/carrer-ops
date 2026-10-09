# Core scoring evaluation harness

Implements the static golden-set runner for FR-EVAL-1 (Phase 3, task 1).
FR-EVAL-2's adversarial soft-relaxation/hard-filter guarantees remain task 2;
this smoke test does not prove them. No memory or personalized scoring is added.

## Run

### Live OpenRouter Mode (Default)

Configure your `.env` file (or set environment variables):
```sh
OPENROUTER_API_KEY="sk-or-v1-..."
OPENROUTER_MODEL="anthropic/claude-3.5-haiku"  # or any tool-calling model
```

Then run the evaluation harness:
```sh
# Run all benchmark queries against live OpenRouter
python3 tests/eval_harness.py

# Run a single query against live OpenRouter
python3 tests/eval_harness.py --case java-fintech

# Use a custom candidate dataset
python3 tests/eval_harness.py --dataset path/to/golden_dataset.json
```

When run live without `--scorer`, it calls OpenRouter for each query, parses the structured `QuerySpec`, validates grounding and schemas, and uses the candidate baseline scorer to evaluate ranking. If OpenRouter is not configured, it exits immediately with instructions.

### Offline Mock Mode

For local smoke testing without API keys or network calls:
```sh
python3 tests/eval_harness.py --mock
python3 tests/eval_harness.py --mock --case resume-week
python3 -m pytest -q
```

**Mock mode is not a benchmark of an LLM or a real scoring engine.** It runs the
existing `app.query_parser.parse_query` through an HTTP mock, replaying separately
stored responses from `tests/eval_mock_parser_outputs.json`. Ranking uses an
explicit test double based on synthetic scalar signals, not semantic similarity.
Neither double reads expected labels. Matching fixtures can score 100%; that only
confirms the runner works, not extraction/ranking quality.

### Real-engine evaluation

This checkout contains the Phase 2 parser but **no Phase 2 scoring engine**.
The harness deliberately does not create a production replacement or silently
report mock rankings as real ones. Once an engine exists, expose an adapter:

```python
async def rank_for_eval(*, query_spec, jobs, profile, as_of):
    # Call the actual Layer 1 engine with these fixed candidates and profile.
    # Adapt its ranked objects to an ordered list of job_id strings.
    ...
```

The adapter may be synchronous or asynchronous. It receives a `QuerySpec`, job
and profile dictionaries, and a fixed ISO-date string; **no expected labels**.
Use an importable `module:function` and configure OpenRouter via environment or
`.env` (tool-calling model required):

```sh
python3 tests/eval_harness.py --scorer app.scoring:rank_for_eval --min-ndcg 0.8
```

`app.scoring:rank_for_eval` is an example integration path, not an existing module.
Real mode calls OpenRouter once per query; provider charges may apply. The adapter
must use only these fixed candidates, not fetch changing live jobs. Any LLM calls
it makes must also go through OpenRouter. Missing adapters/configuration fail
explicitly; no offline fallback is used.

## JSON schema

`tests/golden_dataset.json` contains five synthetic natural-language examples:

- `schema_version`: currently `1`.
- `description`: provenance and limitations.
- `as_of`: fixed reference date for a scorer adapter.
- `top_k`: positive integer cutoff for ranking metrics.
- `profile`: synthetic stored profile facts supplied to the scorer.
- `jobs`: shared candidate pool; each must have a unique `job_id`. Other fields
  are the scorer's input contract. Current fixtures include descriptions, company,
  `age_days` relative to `as_of`, stack, role, industry, tier, seniority, and
  synthetic `signals` used only by the mock scorer.
- `cases`: benchmark objects, each with a unique `id`, `query`,
  `expected_query_spec`, and `expected_top_job_ids`.

`expected_query_spec` uses the existing parser schema: hard filters (`recency_days`,
`tech_stack_keywords`, `role_keywords`, `industries`, `company_names`) and soft
preferences (`factor`, `weight`, `targets`, exact query-substring `evidence`).
Missing hard fields default to null/empty lists. Preferences must have unique
factors. Expected job IDs must be nonempty, unique, and present in the candidate
pool. **List order matters:** earlier IDs have higher relevance grades.

To add a case, independently label its spec and ordered relevant IDs using the
synthetic profile/jobs. If it needs new jobs, add them to the shared pool. To run
it offline, independently add a parser replay response keyed by its ID in
`eval_mock_parser_outputs.json`; do not generate predictions from expected labels.
Use `--dataset path.json` and `--mock-outputs path.json` for alternative fixtures.

## Terminal metrics

Each row shows:
- **Tool**: valid single `emit_query_spec` result accepted by the existing parser.
  Missing/multiple/wrong tool calls, schema violations, and ungrounded preference
  evidence fail through that parser, rather than merely checking final prose.
- **Hard / Soft**: exact group-level matches. List/preference order is ignored;
  factor names, targets, and weights must match exactly. Alternative evidence
  quotes are allowed because the parser checks their grounding independently.
- **P@k**: relevant returned IDs in the first k positions divided by k (missing
  positions count as misses).
- **R@k**: relevant returned IDs in the first k divided by all labeled relevant IDs.
- **NDCG@k**: order-sensitive normalized discounted cumulative gain. Expected
  IDs receive descending grades `n, n-1, ..., 1`; gain is `2^grade - 1`, discounted
  by `log2(position + 1)`. Unlabeled jobs receive zero gain. Ideal order scores 1.

Summary: tool-valid rate, full-spec accuracy (both groups match), and macro-mean
ranking metrics. Labels are a small synthetic benchmark, not empirical career
outcome probabilities. Exceptions stay in the denominator with zero ranking
scores; duplicate/unknown ranked IDs are errors. Parser correctness remains
visible even when scoring fails. Error output identifies stage/type without
printing potentially sensitive upstream response bodies.

Exit codes: `0` for a completed run with matching specs and the requested minimum
mean NDCG; `1` for a case error, spec mismatch, or missed NDCG threshold; `2` for
setup/CLI errors. Default minimum NDCG is zero so exploratory runs can report weak
rankings; use `--min-ndcg` to enforce a ranking-quality gate.
