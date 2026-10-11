"""Match stated job locations; nearby scope is enabled only by the user's query."""
import re


DELHI_NCR = ("delhi", "new delhi", "gurgaon", "gurugram", "noida", "greater noida",
             "faridabad", "ghaziabad", "delhi ncr", "ncr", "national capital region")
CITY_ALIASES = (("delhi", "new delhi"), ("gurgaon", "gurugram"))


def normalized(value: str) -> str:
    return re.sub(r"[\s-]+", " ", value.strip().casefold())


def contains_location(actual: str, required: str) -> bool:
    pattern = re.escape(normalized(required)).replace(r"\ ", r"[\s-]+")
    return bool(re.search(r"(?<!\w)" + pattern + r"(?!\w)", actual.casefold()))


def location_matches(actual: str, required: str) -> bool:
    key = normalized(required)
    aliases = DELHI_NCR if key in ("delhi ncr", "ncr", "national capital region") else next(
        (group for group in CITY_ALIASES if key in group), (required,)
    )
    return any(contains_location(actual, name) for name in aliases)


def query_locations(query: str, locations: list[str]) -> list[str]:
    """'Around Delhi' includes NCR; 'in Delhi' keeps the city's strict filter."""
    nearby = re.search(r"\b(?:around|near|nearby|surrounding)\s+(?:new\s+)?delhi\b", query, re.I)
    ncr = re.search(r"\b(?:delhi[\s-]+ncr|ncr|national capital region)\b", query, re.I)
    negated = re.search(r"\bnot\s+(?:around|near|nearby|surrounding)\s+(?:new\s+)?delhi\b", query, re.I)
    if (nearby or ncr) and not negated:
        converted = ["delhi ncr" if normalized(loc) in ("delhi", "new delhi", "delhi ncr", "ncr") else loc
                     for loc in locations]
        return list(dict.fromkeys(converted))
    return locations
