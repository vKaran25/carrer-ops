# P4 initial audit — 15 October 2026

## Baseline evidence

- Backend: 147 passed, 11 opt-in live checks skipped; isolated fixtures/temporary databases, not live coverage certification.
- Frontend: 25 fictional-fixture browser tests passed; Svelte check 0 errors/0 warnings; production build passed.
- OpenRouter key/model configured; selected model `cohere/north-mini-code:free`. Configuration presence is not a live capability/availability check.
- Tavily key absent at the check. User will configure it manually and notify when ready. Live provider/model checks stay separate; no personal resume uploads or tracker changes were made for this audit.

## Active and deferred surface inventory

| Surface | Current prototype | Target / outstanding work |
|---|---|---|
| Search, resume, chat and Interested | `/api/search`, `/api/resume`, `/api/chat`, job-interest routes; saved independent turns | Structured context and nearby geography now implemented locally; live/strict-city/account acceptance pending |
| Tracker / status / Applied | Jobs/detail/status/mark-applied routes; five stages and draft-dependent critic gate | Four stages, audited Tailored migration, independent Applied recording; no automatic application |
| Preparation and downloads | Tailor/Curate/Research/draft/artifact routes, job detail tabs/buttons | P6; production feature boundary and UI removal pending |
| Learning | Personalization/recalibrate/consent routes and Settings controls | P6; OFF, deny core activation and hide controls in focused UI work |
| Manual LinkedIn | Search-link/import routes and composer buttons | Hide target controls; preserve existing unverified snapshots; no fetching/login/scraping |
| Sources/model configuration | Global source file and operator model catalog exposed through current Settings/API | Operator/user separation and authenticated ownership pending |
| Persistence/auth | SQLite, local user 1, create_all and SQLite-only Applied triggers | Supabase Auth/PostgreSQL, migrations, isolation, deletion and recovery are pending; not safe for public deployment |
| MCP / bots / commercial features | No released MCP/bot/tier integration | P6 / P5B / P5C; none blocks core deployment |

## Confirmed defects fixed in the first increment

1. Tavily malformed root/JSON payloads now produce validation failures rather than unhandled attribute errors.
2. Automatic ATS detection now checks real vendor domain boundaries; lookalike suffixes are not treated as supported providers.
3. Canonical job links reject script schemes, embedded credentials and custom ports.
4. Greenhouse vendor API/job paths preserve the employer token and select the requested requisition instead of fetching a fictitious `v1` board or losing the job.
5. Malformed optional ATS/JSON-LD data no longer discards valid sibling jobs; structured country names are read without displaying raw dictionaries.
6. Static listing cards and missing descriptions remain explicitly unscored. A full JD retrieved later for the same URL takes precedence, without duplicate leads/count inflation. Empty feedback explains missing descriptions honestly.

Regressions reproduced failures before fixes. Post-change backend: **166 passed, 11 opt-in checks skipped**, including 16 source-boundary regressions and 3 benchmark-evaluator checks. That first source-only increment preceded the geography/memory UI changes below. Whitespace checks passed. No live-source quality claim follows.

## Outstanding discovery findings

- Nearby resolution now uses offline GeoNames, a visible default 50 km preference, same-country broadening and 20% location credit; explicit radius limits remain strict. General strict-city alias/ambiguity acceptance remains open. See [geography](geography-and-fit.md).
- New scores open an inline, saved component/point/evidence/location breakdown. No invented per-skill semantic attribution. Legacy cards retain original explanations. Live relevance and location-string coverage remain unverified.
- Dynamic ATS employer labels may be board tokens rather than verified display names; exact company-filter behavior and evidence need further hardening.
- Title-based technology classification can include adjacent non-engineering roles; validate relevance in the independent live benchmark before changing classification rules.
- Static pages without structured JDs become unscored leads; the app does not yet retrieve all platform-only JDs. No all-platform/Indian completeness claim is warranted.
- Workday source caps/date semantics, same-employer cross-platform deduplication and partial-page failures need live verification.
- Source fetching validates public addresses, but production egress/session/worker/operating-limit designs remain discussion checkpoints. This increment does not certify protection against every network attack.

## Next evidence

Use `discovery-benchmark.md` after the user supplies Tavily and the approved location work is integrated. Review quality, verified openings recovered/missed, non-seed employers and actual credits. Poor Indian coverage blocks beta and triggers another discussed source decision. Remaining P4 account, context, UI and operations tasks remain open.

## Geography and structured-memory validation

The installed GeoNames snapshot indexes 236,192 cities (source hashes/timestamp in ignored data/geonames/geography.json). Read-only lookups verified several Indian/international anchors and Delhi-to-Noida/Gurugram/Mumbai distance handling. [Memory implementation](search-context.md) stores explicit intent/defaults separately, supports overrides/removal/reset and conditional revision updates, and commits active context with its chat result. User-facing controls and effective-filter notices are implemented.

Latest backend: **189 passed, 11 opt-in checks skipped**; frontend **27 browser fixture tests passed**; Svelte check **0 errors/0 warnings**; production build **passed**. Desktop/mobile score and memory screenshots were inspected. Live source/model, PostgreSQL/authentication and remaining P4 release acceptance are pending.
