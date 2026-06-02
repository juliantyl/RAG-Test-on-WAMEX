"""Phase 5 (payoff) — "what gold intercepts were reported near these coordinates?"

Joins the extracted intercepts to each report's location (centroid from report_index.csv),
filters by distance + grade, dedupes, and returns rows WITH citations (A-number + page).

Caveat: location granularity is the REPORT footprint centroid, not the drill collar — precise
collar coordinates would come from the drill-data CSVs (a later enhancement). So "near" means
"reported in a report whose footprint centroid is within R km of the point".

Usage:
  python -m src.extract.near <lon> <lat> [radius_km=25] [min_grade=0]
  e.g. python -m src.extract.near 121.47 -30.75 30 5
"""
from __future__ import annotations

import csv
import math
import sys

from src import config as C

INTERCEPTS = C.PROCESSED / "intercepts.csv"
INDEX = C.RAW / "report_index.csv"


def haversine_km(lon1, lat1, lon2, lat2) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _load_centroids() -> dict:
    out = {}
    with INDEX.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            try:
                out[row["anumber"]] = (float(row["centroid_lon"]), float(row["centroid_lat"]))
            except (ValueError, KeyError):
                pass
    return out


def near(lon: float, lat: float, radius_km: float = 25, min_grade: float = 0.0):
    centroids = _load_centroids()
    seen, hits = set(), []
    with INTERCEPTS.open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            loc = centroids.get(r["anumber"])
            if not loc or not r["grade"]:
                continue
            grade = float(r["grade"])
            if grade < min_grade:
                continue
            dist = haversine_km(lon, lat, loc[0], loc[1])
            if dist > radius_km:
                continue
            key = (r["anumber"], r["hole"], r["interval_m"], r["grade"], r["from_m"], r["to_m"])
            if key in seen:           # dedupe cross-page restatements
                continue
            seen.add(key)
            hits.append({**r, "dist_km": round(dist, 1)})
    hits.sort(key=lambda h: (-float(h["grade"]), h["dist_km"]))
    return hits


def main(argv) -> None:
    if len(argv) < 2:
        print("usage: python -m src.extract.near <lon> <lat> [radius_km=25] [min_grade=0]")
        return
    lon, lat = float(argv[0]), float(argv[1])
    radius = float(argv[2]) if len(argv) > 2 else 25.0
    min_grade = float(argv[3]) if len(argv) > 3 else 0.0

    hits = near(lon, lat, radius, min_grade)
    print(f"Gold intercepts within {radius:g} km of ({lon}, {lat}), grade >= {min_grade:g} g/t")
    print(f"-> {len(hits)} intercept(s) [deduped]\n")
    for h in hits[:25]:
        d = f"{h['from_m']}-{h['to_m']}m" if h["from_m"] else "depth n/a"
        print(f"  {float(h['grade']):6.2f} g/t  {h['interval_m']:>5}m  {str(h['hole'] or '?'):10s}"
              f" {h['dist_km']:>5} km   [A{h['anumber']} p{h['page']}]")


if __name__ == "__main__":
    main(sys.argv[1:])
