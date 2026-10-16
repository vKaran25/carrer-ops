"""Offline GeoNames lookup. Never infer coordinates from an LLM or a JD's prose."""
from functools import lru_cache
from contextlib import closing
from math import asin, cos, radians, sin, sqrt
from pathlib import Path
import re
import sqlite3
import unicodedata

from app.config import get_settings


def key(text: str) -> str:
    text = ''.join(c for c in unicodedata.normalize('NFKD', text.casefold()) if not unicodedata.combining(c))
    return re.sub(r'[^\w]+', ' ', text).strip()


class GeographyError(ValueError):
    pass


class Gazetteer:
    def __init__(self, path: str | Path):
        self.path = Path(path).resolve()

    def connect(self):
        if not self.path.is_file():
            raise GeographyError('Nearby search needs the offline geography data. Run python scripts/setup_geography.py, then retry.')
        con = sqlite3.connect(self.path.as_uri() + '?mode=ro', uri=True)
        con.row_factory = sqlite3.Row
        return con

    @lru_cache(maxsize=1)
    def countries(self) -> tuple[dict, ...]:
        with closing(self.connect()) as con:
            return tuple(dict(row) for row in con.execute('SELECT * FROM country'))

    @lru_cache(maxsize=1024)
    def constraint(self, place: str) -> dict:
        if key(place) == 'remote':
            return {'kind': 'remote'}
        countries = [c for c in self.countries() if key(place) in {key(c[n]) for n in ('name', 'code', 'iso3') if c[n]}]
        if len(countries) == 1:
            return {'kind': 'country', **countries[0]}
        return {'kind': 'city', **self.resolve(place)}

    @lru_cache(maxsize=2048)
    def candidates(self, place: str) -> tuple[dict, ...]:
        parts = [key(p) for p in re.split(r'[,;|/]', place) if key(p)]
        if not parts:
            return ()
        with closing(self.connect()) as con:
            # First part is the city; remaining parts must name its country/state.
            rows = con.execute('SELECT DISTINCT c.* FROM city c JOIN alias a ON a.city_id=c.id WHERE a.name=?', (parts[0],)).fetchall()
        result = []
        for row in rows:
            city = dict(row)
            qualifiers = {key(city[n]) for n in ('country', 'country_code', 'country_iso3', 'admin', 'admin_code') if city[n]}
            if all(p in qualifiers for p in parts[1:]):
                result.append(city)
        # Prefer a city's official/ascii name over a historical alias collision.
        exact = [c for c in result if parts[0] in (key(c['name']), key(c['ascii_name']))]
        return tuple(exact or result)

    def resolve(self, place: str) -> dict:
        rows = self.candidates(place)
        if len(rows) == 1:
            return rows[0]
        if not rows:
            raise GeographyError(f'Could not resolve “{place}” in the offline city data. Specify a city, state and country, or another nearby city.')
        options = '; '.join(dict.fromkeys(f"{c['name']}, {c['admin']}, {c['country']}" for c in rows[:6]))
        raise GeographyError(f'“{place}” is ambiguous. Add the state/country to your query. Options: {options}.')

    @lru_cache(maxsize=1)
    def admin_codes(self) -> frozenset[str]:
        with closing(self.connect()) as con:
            return frozenset(row[0] for row in con.execute('SELECT DISTINCT admin_code FROM city') if row[0])

    @lru_cache(maxsize=4096)
    def job_places(self, location: str) -> tuple[tuple[dict, ...], frozenset[str]]:
        """Use explicit location labels, with conservative treatment of state/country codes."""
        cities, countries = {}, set()
        catalog = self.countries()
        for chunk in re.split(r'[;|/]|\s+or\s+', location, flags=re.I):
            cleaned = re.sub(r'\b(?:remote|hybrid|onsite|on-site)\b[: -]*', '', chunk, flags=re.I).strip(' ,()')
            cleaned = re.sub(r'\s+-\s+', ', ', cleaned)
            if not cleaned:
                continue
            parts = [part.strip() for part in cleaned.split(',') if part.strip()]
            if not parts:
                continue
            explicit = [c for c in catalog if key(cleaned) in {key(c['name']), key(c['iso3'])}]
            if len(explicit) == 1:
                code = explicit[0]['code']
                countries.add(code)
                rows = [c for c in self.candidates(cleaned) if c['country_code'] == code]
                if len(rows) == 1:
                    cities[rows[0]['id']] = rows[0]
                continue
            rows = self.candidates(cleaned)
            if len(rows) == 1:
                cities[rows[0]['id']] = rows[0]
                countries.add(rows[0]['country_code'])
                continue
            first = self.candidates(parts[0])
            named = [c for c in catalog if key(parts[-1]) in {key(c['name']), key(c['iso3'])}]
            last_codes = [c for c in catalog if parts[-1] == c['code']]
            # A trailing ISO code needs a supporting city, or an unambiguous
            # standalone country code. Middle state codes never assert a country.
            supported_codes = [c for c in last_codes if any(city['country_code']==c['code'] for city in first)
                               or len(parts)==1 and c['code'] not in self.admin_codes()]
            asserted = {c['code'] for c in named + supported_codes}
            countries.update(asserted)
            qualified = [c for c in first if c['country_code'] in asserted]
            if len(qualified) == 1:
                city = qualified[0]
                # Known contradictory state names cannot be discarded as abbreviations.
                with closing(self.connect()) as con:
                    known_admins = {key(row[0]) for row in con.execute('SELECT DISTINCT admin FROM city WHERE country_code=?', (city['country_code'],))}
                if any(key(p) in known_admins and key(p) != key(city['admin']) for p in parts[1:-1]):
                    continue
                cities[city['id']] = city
        return tuple(cities.values()), frozenset(countries)

    def matches(self, actual: str, required: str) -> bool:
        constraint = self.constraint(required)
        if constraint['kind'] == 'remote':
            return bool(re.search(r'\bremote\b', actual, re.I))
        cities, countries = self.job_places(actual)
        if constraint['kind'] == 'country':
            return constraint['code'] in countries
        return any(c['id'] == constraint['id'] for c in cities)


@lru_cache(maxsize=4)
def gazetteer(path: str | None = None) -> Gazetteer:
    return Gazetteer(path or get_settings().geonames_db)


def distance_km(a: dict, b: dict) -> float:
    lat1, lat2 = radians(a['latitude']), radians(b['latitude'])
    delta_lat, delta_lon = lat2-lat1, radians(b['longitude']-a['longitude'])
    value = sin(delta_lat/2)**2 + cos(lat1)*cos(lat2)*sin(delta_lon/2)**2
    return 6371.0088 * 2 * asin(sqrt(min(1., max(0., value))))


def location_assessment(location: str, scope) -> dict:
    geo = gazetteer()
    anchor = geo.resolve(scope.place)
    cities, countries = geo.job_places(location)
    distances = [(distance_km(anchor, c), c) for c in cities if c['country_code'] == anchor['country_code']]
    closest = min(distances, key=lambda pair: pair[0]) if distances else None
    distance = closest[0] if closest else None
    same_country = anchor['country_code'] in countries
    within = distance is not None and distance <= scope.radius_km
    credit = (1. if within else min(1., scope.radius_km / distance)) if distance is not None else 0.
    label = f"{anchor['name']}, {anchor['country']}"
    if distance is not None:
        detail = f"{closest[1]['name']}: approximately {distance:.1f} km from {label}; {'inside' if within else 'outside'} the {scope.radius_km:g} km radius."
    else:
        detail = 'City distance is unknown; no location points awarded. ' + ('Country is evidenced.' if same_country else 'The required country is not evidenced.')
    return {'anchor': label, 'country': anchor['country'], 'radius_km': scope.radius_km,
            'mode': scope.mode, 'distance_km': round(distance, 1) if distance is not None else None,
            'within_radius': within, 'same_country': same_country, 'credit': credit,
            'evidence': detail + ' Distance uses GeoNames city centres in a straight line, not travel distance.'}
