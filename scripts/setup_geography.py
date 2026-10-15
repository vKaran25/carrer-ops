"""Build an offline city index from official GeoNames downloads (CC BY 4.0)."""
import argparse
from contextlib import closing
from datetime import datetime, timezone
from hashlib import sha256
import io
import json
from pathlib import Path
import sqlite3
import sys
from urllib.request import urlopen
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.geography import key

BASE = 'https://download.geonames.org/export/dump/'
ATTRIBUTION = 'GeoNames, https://www.geonames.org/, CC BY 4.0 https://creativecommons.org/licenses/by/4.0/. Modified into a city/alias lookup index.'


def build_index(city_lines, country_lines, admin_lines, target):
    countries, admins = {}, {}
    for line in country_lines:
        if line.startswith('#') or not line.strip():
            continue
        row = line.rstrip('\n').split('\t')
        countries[row[0]] = (row[4], row[1])
    for line in admin_lines:
        row = line.rstrip('\n').split('\t')
        if len(row) >= 3:
            admins[row[0]] = row[1]
    with closing(sqlite3.connect(target)) as con:
        con.executescript('''CREATE TABLE country(code TEXT PRIMARY KEY, name TEXT, iso3 TEXT);
            CREATE TABLE city(id INTEGER PRIMARY KEY, name TEXT, ascii_name TEXT, latitude REAL, longitude REAL,
              country_code TEXT, country TEXT, country_iso3 TEXT, admin TEXT, admin_code TEXT);
            CREATE TABLE alias(name TEXT, city_id INTEGER, PRIMARY KEY(name, city_id));''')
        con.executemany('INSERT INTO country VALUES(?,?,?)', [(code, name, iso3) for code, (name, iso3) in countries.items()])
        for line in city_lines:
            row = line.rstrip('\n').split('\t')
            if len(row) < 19 or row[8] not in countries:
                continue
            country, iso3 = countries[row[8]]
            con.execute('INSERT INTO city VALUES(?,?,?,?,?,?,?,?,?,?)', (int(row[0]), row[1], row[2], float(row[4]), float(row[5]),
                        row[8], country, iso3, admins.get(row[8]+'.'+row[10], ''), row[10]))
            names = {key(n) for n in [row[1], row[2], *row[3].split(',')] if key(n)}
            con.executemany('INSERT OR IGNORE INTO alias VALUES(?,?)', [(name, int(row[0])) for name in names])
        con.commit()
        return con.execute('SELECT COUNT(*) FROM city').fetchone()[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='data/geonames/geography.sqlite')
    args = parser.parse_args()
    target = Path(args.output).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_suffix('.building')
    if temp.exists():
        raise SystemExit(f'Incomplete build already exists: {temp}. Inspect/remove it before retrying.')
    blobs, metadata = {}, {}
    for name in ('cities500.zip', 'countryInfo.txt', 'admin1CodesASCII.txt'):
        with urlopen(BASE+name, timeout=120) as response:
            blob = response.read(100_000_001)
        if len(blob) > 100_000_000:
            raise SystemExit('GeoNames download exceeded the 100 MB per-file limit')
        blobs[name] = blob
        metadata[name] = {'url': BASE+name, 'sha256': sha256(blob).hexdigest(), 'bytes': len(blob)}
    try:
        with ZipFile(io.BytesIO(blobs['cities500.zip'])) as archive:
            if archive.getinfo('cities500.txt').file_size > 400_000_000:
                raise ValueError('City data exceeded the 400 MB limit')
            with archive.open('cities500.txt') as raw:
                count = build_index(io.TextIOWrapper(raw, encoding='utf-8'), blobs['countryInfo.txt'].decode('utf-8').splitlines(),
                                    blobs['admin1CodesASCII.txt'].decode('utf-8').splitlines(), temp)
        temp.replace(target)
    except BaseException:
        if temp.exists():
            temp.unlink()
        raise
    metadata.update(downloaded_at=datetime.now(timezone.utc).isoformat(), cities=count, attribution=ATTRIBUTION)
    target.with_suffix('.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
    print(f'Indexed {count} cities at {target}\n{ATTRIBUTION}')


if __name__ == '__main__':
    main()
