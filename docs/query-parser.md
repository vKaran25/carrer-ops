# Query parser (Phase 2, task 1)

`app/query_parser.py` exposes `await parse_query(query) -> QuerySpec`.
It makes one OpenRouter chat-completions request with a forced function call;
there are no retries, heuristic fallback, search integration, or scoring yet.
Configure `OPENROUTER_API_KEY` and `OPENROUTER_MODEL` in the environment or `.env`.
Choose a model supporting tool calling. Unsupported parameters/providers fail
explicitly rather than silently falling back to unstructured text.

The result has:
- `hard_filters`: `recency_days`, `tech_stack_keywords`, `role_keywords`,
  `industries`, `company_names`. Missing filters are null/empty lists.
- `soft_preferences`: `factor`, independent positive `weight` (at most 1),
  `targets`, and an exact supporting `evidence` quote from the query.

Company tier and seniority are always soft, never fields in hard filters.
Resume-company affinity does not invent company names. Resume/project facts are
not available to the parser; preferences referencing them are symbolic factors
for later scoring. A week or two uses the inclusive 14-day recency window;
this week uses a rolling 7-day window. Weights encode primary (1.0) versus
supporting (0.5) priorities, not probabilities or hard eligibility thresholds.
Invalid output, ungrounded preference quotes, and upstream failures raise
`QueryParserError`. Blank queries raise `ValueError` before any request.

## Tests

```sh
python3 -m pytest -q
# Requires valid OpenRouter configuration; makes five actual paid/provider calls:
RUN_LIVE_QUERY_TESTS=1 python3 -m pytest -q tests/test_query_parser.py -k live
```

The default tests use mocked tool outputs for all five spec examples, validating
transport, schema, expected factor distinctions, and failure handling. These do
not establish live model extraction quality. The opt-in live test submits all
five natural-language queries and checks the extracted constraints/preferences.
The broader spec's ranked-list/relaxation acceptance criterion belongs to tasks
2–3, not this standalone parser.
