# Career Ops

A local FastAPI + LangGraph + SvelteKit job-search workspace. Implementation covers Phases 1–3; real generative acceptance still needs a configured free OpenRouter model. See [acceptance status](docs/implementation-status.md).

## Setup and run

Use Python 3.11 and Node 22.12+. From the repository root on macOS:

```sh
uv venv --python 3.11
uv pip sync --python .venv/bin/python requirements.lock
.venv/bin/python -m playwright install chromium
brew install tectonic
npm --prefix frontend ci
.venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

In a second terminal run `npm --prefix frontend run dev`, then open **http://127.0.0.1:5173**. API documentation: http://127.0.0.1:8000/docs. The frontend proxies /api to the backend; set BACKEND_URL in its process to use another backend address.

Keyword search works without an API key or resume. Local BGE embeddings download when first needed. Tectonic's first compilation may download fonts and packages.

## Free OpenRouter configuration

Copy .env.example to .env, add your key, and select an actual current free model supporting tool calling. Settings → **Check current free tool models** reads the public catalog without a key. Select a listed ID ending in :free; openrouter/free is also accepted as the free router. Restart the backend after changing .env.

Paid model IDs are rejected before requests. Every generative call forces a function result, requires parameter support, denies provider data collection, and caps prompt/completion/per-request prices at zero. Provider errors are shown explicitly. Free model availability and quotas may change. [Free variants](https://openrouter.ai/docs/guides/routing/model-variants/free), [provider routing](https://openrouter.ai/docs/guides/routing/provider-selection).

## Behavior

- Search real tech postings worldwide from configured company pages. Initial sources: Canonical, Cloudflare, Vercel. Add companies in Settings. Coverage is these sources, not the entire internet.
- Required technology, role, company, industry, location and publication dates stay strict. Weak soft matches remain visible at lower fit. Unknown publication dates cannot satisfy recency. Scores measure content match, not hiring probability.
- New results enter the tracker and are deduplicated from future discoveries. Search never automatically tailors, curates, researches or submits applications.
- Upload .tex, text-readable PDF, .docx or .txt. Facts must be exact source quotations. Scanned PDFs need a text-readable version.
- Tailor/curate only a requested single job. Drafts select or combine whole stored statements and pass provenance validation plus an independent critic. Verified draft/JD similarity makes a small, disclosed content-fit adjustment after tailoring. No qualifications are invented.
- LaTeX curation preserves all source outside supported statement spans. PDF/Word intake uses an honestly labeled new layout. Columns/tables receive an advisory while layout stays preserved. PDF and .tex downloads are provided. Only self-contained LaTeX is supported.
- **Mark as applied** records your explicit action; it does not submit anything externally. Fix or discard a failed current draft first. Stages and outcomes persist in SQLite.
- Interview research runs on demand, uses fixed public queries, validates quoted company-specific evidence, and caches results for 60 days. Unsupported rounds/questions produce insufficient information. Public reports are anecdotal, not a guaranteed process.
- Memory consolidates current facts and explicit outcomes using add/update/delete. Local model learning stays **off**, as requested. The implemented Phase 3 scorer requires an optional Settings opt-in; turning it off deletes learned weights.

Data lives in data/ and is excluded from Git. This is a single local user workspace. Authentication, bots, monetization and public deployment remain out of scope.

## Checks without LLM calls

```sh
.venv/bin/python -m pytest -q
.venv/bin/python tests/eval_harness.py --offline-engine --min-ndcg 0.8
npm --prefix frontend run check
npm --prefix frontend run build
npm --prefix frontend exec playwright install chromium
npm --prefix frontend test
RUN_LIVE_SOURCE_TESTS=1 .venv/bin/python -m pytest -q tests/test_live_sources.py
```

Python workflow tests run the actual API, graph, SQLite, embeddings and PDF compiler with fixture model responses. Browser tests use explicitly fictional API fixtures. They neither claim live model quality nor seed your workspace. Inspect skips if compiler/browser prerequisites are missing elsewhere.

## Real free-model acceptance after configuring .env

```sh
RUN_LIVE_QUERY_TESTS=1 .venv/bin/python -m pytest -q tests/test_query_parser.py -k live
RUN_LIVE_LLM_TESTS=1 .venv/bin/python -m pytest -q tests/test_live_workflows.py
.venv/bin/python tests/eval_harness.py --min-ndcg 0.8 --persist
```

Zero-price/privacy restrictions remain enforced. Live workflow tests use temporary databases and fictional resumes, fetch real jobs and exercise the graph, critic, explicit gate, two-JD LaTeX curation and public company research. Provider/source failures fail these tests; there is no synthetic fallback and no external application submission. Golden evaluation uses fixed fictional candidates; --persist saves EvalRun metrics locally.

Details: [parser](docs/query-parser.md), [evaluation](docs/eval-harness.md), [memory](docs/memory-and-personalization.md).
