# Implementation and acceptance status

## Scope and confirmed decisions

The original checkout contained a backend health scaffold, query parser and partial evaluation harness. The user authorized restoring Phase 1 prerequisites and implementing through Phase 3, including UI and acceptance tests. Phase 4/5 remain out of scope.

UI: light blue workspace, sidebar Search / Job tracker / Resume / Settings, details beside results, Kanban/list toggle. Worldwide tech postings from configured sources. Local embeddings approved. Strict hard filters, lower-scoring soft matches retained. Exact stored statements only for drafts/curation. Preserve LaTeX layout with a column/table advisory. Only free OpenRouter models. Isolated fictional fixtures allowed. Local outcome-based learning stays off at the user's request; its consent-gated implementation is available for later use.

## Acceptance evidence

| Module | Implementation and checks | Live limitation |
|---|---|---|
| P1 graph / getting started | Real API/graph search → tailor → critic → explicit gate tests; optional resume | Real model loop pending key |
| P1 scout | Posting contract, varied query fixtures, static crawler, caps and tracker deduplication tested | Public ATS checks passed |
| P1 tailor / critic | Two distinct JD drafts, exact fact IDs, planted fabrication rejection; verified draft contributes to content fit | Actual model selection/criticism pending key |
| P1 gate | Explicit action, persistent audit, SQLite status triggers; API false-action and direct database bypass rejection tested | No external submissions |
| P1 tracker | Five stages, outcomes, Kanban/list; fresh-session storage and browser reload/update tests | Local single-user scope |
| P2 query | Five distinct forced-tool parser fixtures and invalid-tool/schema checks | Live five-query extraction pending key |
| P2 scoring | Actual local embeddings, grounded signals, strict filters, soft relaxation; adversarial dates, Java/JavaScript, unknown tier and impossible hard filters tested | Golden set is fictional and small |
| P2 ATS | Greenhouse/Lever/Workday JSON first, BS4 then logged Playwright; actual Chromium JS fixture passed | Real Canonical/Vercel/Cloudflare, Spotify and NVIDIA source checks passed |
| P2 research | Fixed queries, single synthesis, company filtering, exact evidence, shared 60-day cache and explicit insufficient-data checks | Live documented/obscure-company acceptance pending key and source availability |
| P2 curator | Stable IDs/spans, exact-fact edits, critic, PDF/tex, honest template fork and ATS advisory; two-JD edits preserve surrounding source; real Tectonic render/download/extraction tested | Actual model plans pending key |
| P3 memory | Stable source keys and add/update/delete; replacements, corrections and deletion tested | No invented facts/outcomes |
| P3 scorer | Per-user bounded batch model, six-outcome cold start, five-new-outcome/on-demand refit; fixture ranking changes, user isolation, opt-in/revocation tested | OFF in real workspace as requested |
| P3 evaluation | Tool/spec metrics plus actual ranking adapter, optional EvalRun persistence and adversarial filter tests | Real parser benchmark pending key |
| UI | Four responsive pages, empty/error states, explicit actions and provenance; 13 Chromium checks pass | Browser API responses are fictional fixtures |

## Recorded results

- Backend suite: **93 passed, 9 skipped** in the default run (5 public-source and 4 real-model opt-in checks).
- Public source suite: **5 passed** for Greenhouse, Lever and Workday. A separate real API/graph keyword search returned three real postings without source warnings in an isolated database.
- Actual local ranking with replayed parser: **5 cases**, P@2/R@2 **0.900**, NDCG@2 **0.965**.
- Browser suite: **13 passed**.
- Svelte diagnostics: **0 errors, 0 warnings**.
- Production frontend build: **passed**.
- Browser smoke check against the actual backend: all four pages opened, zero JavaScript errors, local learning confirmed off.

Replayed parser tool/spec accuracy is 100%; this is not live LLM accuracy. The Java/fintech benchmark ranks an older eligible role above one labeled banking role. There is no recency hard filter in that case; labels were not changed to improve the result. Scores are not empirical hiring probabilities.

## Remaining live acceptance

No OpenRouter key/model is configured, so no real generative calls were made and no credits were spent. Implementation through P3 is present with local learning disabled, but full live LLM acceptance is not certified. [README](../README.md) provides opt-in commands for live parsing, the complete graph loop, two-JD curation, company research and the golden evaluation.

Practical limits: configured and bounded source coverage; unknown publication dates cannot satisfy recency; public APIs/search may change or block access; scanned PDFs and arbitrary LaTeX macros/external files are unsupported. The workspace is local and single-user.
