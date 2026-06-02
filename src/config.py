"""Central config: paths, study region, WAMEX endpoints, retrieval settings.

Project 2 = RAG over WAMEX open-file exploration reports, gold / Eastern Goldfields
(same region as Project 1, so the two can be cross-referenced).
"""
from __future__ import annotations

from pathlib import Path

# ----------------------------------------------------------------------------
# Paths
# ----------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RAW = DATA / "raw"           # downloaded report PDFs + metadata (gitignored)
INTERIM = DATA / "interim"   # extracted page text, chunks
PROCESSED = DATA / "processed"  # embeddings index, extracted assay schema
OUTPUTS = ROOT / "outputs"

for _p in (RAW, INTERIM, PROCESSED, OUTPUTS):
    _p.mkdir(parents=True, exist_ok=True)

# ----------------------------------------------------------------------------
# Study region — Eastern Goldfields (lon/lat, matches Project 1)
# ----------------------------------------------------------------------------
BBOX_GEO = (120.5, -31.5, 122.5, -30.0)   # (min_lon, min_lat, max_lon, max_lat)
CRS_GEO = "EPSG:4326"

# ----------------------------------------------------------------------------
# WAMEX spatial index (DMIRS via SLIP) — ArcGIS FeatureLayer, JSON/geoJSON query.
# Fields: anumber, title, report_year, author_company, operator, project, abstract,
#         keywords, target_commodity, digital_file (-1 = has digital file, 0 = not),
#         dpxe_rep (report-details page URL).  Max 10,000 records/query.
# ----------------------------------------------------------------------------
WAMEX_LAYER = ("https://services.slip.wa.gov.au/public/rest/services/"
               "SLIP_Public_Services/Industry_and_Mining/MapServer/22/query")
WAMEX_REPORT_DETAILS = "https://wamex.dmp.wa.gov.au/Wamex/Search/ReportDetails?ANumber={anumber}"

# Slice filters — keep the corpus small and focused so effort goes into RAG, not data.
SLICE_WHERE = "target_commodity LIKE '%GOLD%' AND digital_file=-1 AND report_year>=2018"
SLICE_BBOX = (121.0, -31.0, 121.7, -30.5)  # tighter sub-area (Coolgardie–Kalgoorlie belt)
MAX_REPORTS = 30                            # cap the slice

# ----------------------------------------------------------------------------
# Retrieval / embeddings (all local + free)
# ----------------------------------------------------------------------------
EMBED_MODEL = "BAAI/bge-small-en-v1.5"   # small, strong English embedder; swappable
CHUNK_TOKENS = 350                        # ~target chunk size (chars approximated later)
CHUNK_OVERLAP = 60
TOP_K = 8

SEED = 42
