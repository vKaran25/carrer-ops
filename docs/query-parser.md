# Query parsing and search

Release note (15 October 2026): this describes the existing standalone-query parser. The local P4 structured-context layer now handles follow-ups and explicit saved defaults before discovery; production account binding remains pending. See [search context](search-context.md). See [core requirements](../spec/core-release.md). The nearby GeoNames increment is implemented; general strict-city and live Indian coverage acceptance remain release work. See [geography and fit](geography-and-fit.md).

await app.query_parser.parse_query(query) returns QuerySpec through one forced OpenRouter function call. There are no retries or silent fallbacks. Models must be free and support tools. Requests require parameter support, deny provider data collection and cap prompt/completion/request prices at zero.

Hard fields: recency_days, tech_stack_keywords, role_keywords, industries, company_names, locations. Soft fields: factor, weight, targets and exact query-substring evidence. Company tier and seniority are soft. Resume/company/project references do not invent names. A week or two means 14 days; this week means seven. Absent hard fields remain null/empty.

The graph passes specs into discovery and app.scoring.rank_jobs. Hard filters never relax. Weak or unknown soft matches reduce fit but remain eligible. Impossible hard constraints yield honest empty results. Explicit keyword mode is a separate limited technology/role parser; it does not interpret natural-language location, industry or recency and is never a silent model fallback.

Invalid schemas, wrong/multiple tools, unsupported preference evidence, duplicate factors and upstream failures raise QueryParserError. The API reports failure instead of inventing interpretations or results.

```sh
.venv/bin/python -m pytest -q tests/test_query_parser.py tests/test_scoring.py
RUN_LIVE_QUERY_TESTS=1 .venv/bin/python -m pytest -q tests/test_query_parser.py -k live
```

The default parser tests use independently stored tool-response fixtures and do not establish live extraction quality. The opt-in test submits the five example queries to a configured free model.

`location_scope` is optional: explicit city/state/country `place`, default `radius_km=50`, `mode=preferred|required`, exact query `evidence`. Parser validation rejects ungrounded places/radii and softened explicit distance boundaries. Backend GeoNames resolution occurs before source discovery; missing/ambiguous anchors produce a 422 clarification/setup error. Nearby anchor cities must not also be emitted as strict city filters. Live free-model behavior for this added field remains pending.
