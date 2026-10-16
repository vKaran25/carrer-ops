"""Explain empty results using recorded retrieval/filter data, without guessing."""


def empty_search_message(result: dict) -> str:
    if result.get("jobs"):
        return ""
    stats = result.get("search_stats", {})
    scope = 'checked sources (company boards and web discovery)' if stats.get('web_queries') else 'checked company sources'
    excluded = result.get("excluded", {})
    locations = result.get("query_spec", {}).get("hard_filters", {}).get("locations", [])
    location_label = ", ".join(loc.title().replace("Ncr", "NCR") for loc in locations)
    if result.get('external_links') and stats.get('description_unavailable') and not excluded:
        return 'Listings were found, but their full job descriptions could not be verified for scoring. The links below are unscored; required filters and availability are unverified.'
    if stats.get("sources_searched") == 0 and not stats.get('web_queries'):
        return "No enabled source could be searched. Check service status and the source notices."
    if stats and stats.get("retrieved", 0) == 0:
        if result.get('external_links'):
            return 'Discovered links are shown below, but their full job details could not be retrieved for scoring. Check the original listing for details.'
        return f"No postings were retrieved from the {scope}. See the source notices and service status."
    if excluded.get("Different required location") and location_label:
        return f"No new roles met your required location ({location_label}) and other filters in the {scope}."
    if excluded:
        return f"No new roles met your required filters in the {scope}. Your filters were kept."
    if stats.get("already_tracked", 0) and stats.get("already_tracked") == stats.get("tech_jobs"):
        return "All tech roles retrieved from these company sources are already in your tracker."
    return f"No new tech roles were found in the {scope}. Coverage may be incomplete; try another query or location."
