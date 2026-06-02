"""Phase 1 — fetch the WAMEX metadata slice (no PDFs yet; downloads are manual).

Queries the WAMEX spatial index for our gold / Eastern-Goldfields slice and writes a tidy
index (data/raw/report_index.csv) with each report's A-number, title, year, operator,
commodity, abstract, centroid coords, and its ReportDetails page URL. Then prints a download
checklist: which A-numbers to request via the WAMEX email-a-ZIP form and where to drop them.

Run:  python -m src.ingest.fetch_metadata
"""
from __future__ import annotations

import csv

import requests

from src import config as C

OUT = C.RAW / "report_index.csv"
FIELDS = ["anumber", "title", "report_year", "operator", "author_company",
          "project", "target_commodity", "abstract", "dpxe_rep"]


def _centroid(feat) -> tuple[float | None, float | None]:
    """Centroid lon/lat: prefer server 'centroid', else average polygon ring vertices."""
    if feat.get("centroid"):
        return round(feat["centroid"]["x"], 5), round(feat["centroid"]["y"], 5)
    geom = feat.get("geometry") or {}
    rings = geom.get("rings")
    if rings:
        pts = [p for ring in rings for p in ring]
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
        return round(sum(xs) / len(xs), 5), round(sum(ys) / len(ys), 5)
    return None, None


def fetch() -> list[dict]:
    bbox = ",".join(str(v) for v in C.SLICE_BBOX)
    common = {
        "where": C.SLICE_WHERE,
        "geometry": bbox, "geometryType": "esriGeometryEnvelope", "inSR": "4326",
        "spatialRel": "esriSpatialRelIntersects", "outSR": "4326", "f": "json",
    }
    total = requests.get(C.WAMEX_LAYER, params={**common, "returnCountOnly": "true"}, timeout=120).json()
    print(f"reports matching slice filter: {total.get('count')}  (capping to {C.MAX_REPORTS})")

    params = {**common, "outFields": ",".join(FIELDS), "returnGeometry": "true",
              "returnCentroid": "true", "orderByFields": "report_year DESC",
              "resultRecordCount": str(C.MAX_REPORTS)}
    feats = requests.get(C.WAMEX_LAYER, params=params, timeout=120).json().get("features", [])

    rows = []
    for f in feats:
        a = dict(f["attributes"])
        lon, lat = _centroid(f)
        a["centroid_lon"], a["centroid_lat"] = lon, lat
        a["details_url"] = C.WAMEX_REPORT_DETAILS.format(anumber=a["anumber"])
        rows.append(a)
    return rows


def main() -> None:
    rows = fetch()
    cols = FIELDS + ["centroid_lon", "centroid_lat", "details_url"]
    with OUT.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"[ok] wrote {OUT}  ({len(rows)} reports)\n")

    print("=" * 78)
    print("DOWNLOAD CHECKLIST — request each report's ZIP via the email form, then unzip")
    print(f"its PDFs into:  {C.RAW}\\A<anumber>\\")
    print("=" * 78)
    for r in rows:
        title = (r.get("title") or "")[:64]
        print(f"  A{r['anumber']:<7} {r.get('report_year'):<5} {title}")
        print(f"           {r['details_url']}")


if __name__ == "__main__":
    main()
