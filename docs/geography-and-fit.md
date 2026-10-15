# Nearby search and fit explanations — P4 increment

## Approved behavior

“Around/near a city” prefers a 50 km radius by default. The query can supply a different radius in kilometres. Eligible jobs farther away can appear **within the anchor city's country**. An explicit “within 25 km only” is a mandatory boundary: unknown/outside distances fail it. Other explicit technology/date/company/location filters remain mandatory. Plain “in a city” retains its existing strict city filtering; it does not acquire nearby broadening.

For a nearby preference:

```text
location_credit = 1                         if distance <= radius
                  radius / distance        if distance > radius
                  0                        if city distance is unknown
overall_fit = 100 * (0.80 * existing_relevance + 0.20 * location_credit)
```

Country evidence is still required when distance is unknown. A country-only location such as “Remote, India” can remain at zero location credit; “Remote” alone cannot establish India. Unambiguous city identity can establish country through the index. Multi-site jobs use their closest resolved site within the anchor country. No cross-border broadening.

The existing relevance calculation is unchanged: semantic resume match alone, or 65% semantic baseline plus 35% weighted query preferences when supplied. A mandatory radius filters eligibility without adding the optional 20% preference weight. Learned adjustment remains an OFF, deferred prototype.

## Offline setup

From the repository root on Windows:

```powershell
.venv/Scripts/python.exe scripts/setup_geography.py
```

The installer downloads official `cities500.zip`, `countryInfo.txt` and `admin1CodesASCII.txt`, builds `data/geonames/geography.sqlite`, and writes download timestamps, SHA-256 hashes and attribution to `geography.json`. The first installed snapshot contains **236,192 cities**, about **82 MB** for the derived index. Files are ignored by Git. Set `GEONAMES_DB` to override the index path. Download/build happens explicitly, not during user searches. Restart the backend after installing/replacing the index so process caches use the new snapshot.

Runtime opens the index read-only. Missing data gives a setup error. Ambiguous anchors ask for a state/country, with candidate labels. Unknown/ambiguous job cities get no invented coordinates; an evidenced country alone does not establish a distance. Commas qualify a city; semicolons/slashes separate work sites. Dataset coverage, city-centre coordinates, historical aliases and inconsistent source location strings have limits. This is approximate straight-line distance, not commute distance, a legal metro boundary or evidence that a remote role permits work from the user's location.

Primary source and attribution: [GeoNames download documentation](https://download.geonames.org/export/dump/readme.txt), [GeoNames](https://www.geonames.org/), [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The source is transformed into a city/alias lookup index. Attribution also appears in job score details.

## Score details and persistence

Click a job's score to open its existing card and inline explanation. New search snapshots include factor values, effective weights, actual point contributions, rounding/cap adjustment, exact stored resume comparison inputs, query evidence and location/unknown-data handling. Values and points are formatted for display; the stored raw contributions reconcile with the final score. Scores are content relevance, never hiring probabilities. Semantic encoding compares up to 24,000 characters per input; individual skills/statements do not receive fabricated numerical contributions.

The breakdown uses existing chat-result JSON, with no new account database table or migration. It survives refresh. Historical searches without it retain their original explanation and recommend a new search for detailed points. Resume replacement/removal hides stale breakdowns, signals, preferences and scores while retaining historical JDs and tracker progress. Interested remains the only tracker intake; tracker explanation text includes actual points, while structured breakdowns currently live in chat snapshots.

## Verification and remaining acceptance

- Isolated fictional geography tests cover aliases/qualifiers, ambiguity, missing index, same-country broadening, unknown distance, strict radius, custom radius/evidence validation, weighted arithmetic, existing soft-preference mix, multiple work sites, country-level retrieval queries and filtering before the scout cap.
- Chat fixture tests cover saved breakdowns and stale evidence invalidation.
- Browser fixtures cover clicking/keyboard activation, desktop/mobile layout, refresh and zero automatic tracker additions.
- Read-only real-index checks resolved Delhi/New Delhi, Pune, Bengaluru, Kochi, London and Toronto; Delhi to Noida/Gurugram falls inside 50 km and Mumbai outside. These checks are lookup evidence, not live job-search evidence.
- Live free-model interpretation of these new fields, real Tavily discovery/relevance and broad location-string coverage remain pending. The legacy strict city/NCR matcher remains for existing filters; fully general strict-city alias/ambiguity acceptance is still open. Dataset geography does not complete P4 account/context/UI/operations acceptance.

After live-provider testing is authorized, try “Python backend jobs around Delhi, India”, “Python backend jobs within 25 km of Delhi, India only”, and “jobs around London” (clarification). Check source locations, labels, points and original JD evidence; a correctly empty strict search is valid.
