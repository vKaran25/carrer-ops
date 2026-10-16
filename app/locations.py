"""Match stated job locations; nearby scope is enabled only by the user's query."""
import re


def normalized(value: str) -> str:
    return re.sub(r"[\s-]+", " ", value.strip().casefold())


def contains_location(actual: str, required: str) -> bool:
    pattern = re.escape(normalized(required)).replace(r"\ ", r"[\s-]+")
    return bool(re.search(r"(?<!\w)" + pattern + r"(?!\w)", actual.casefold()))


def location_matches(actual: str, required: str) -> bool:
    from app.geography import gazetteer
    return gazetteer().matches(actual, required)


def query_locations(query: str, locations: list[str]) -> list[str]:
    """Compatibility helper: no city-specific broadening of strict filters."""
    return locations
