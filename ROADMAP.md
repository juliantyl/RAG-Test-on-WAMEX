# RAG over WAMEX Exploration Reports — Roadmap

**Goal:** ingest a slice of WAMEX (WA open-file mineral-exploration reports) and answer questions
like *"what gold intercepts were reported near these coordinates?"* with **cited sources**.

**Slice:** gold reports in the Eastern Goldfields (same region as Project 1's prospectivity model,
so the two projects can talk to each other).

**Why this is hard (and worth doing):** the corpus is tens of thousands of scanned, OCR'd,
inconsistently-formatted PDFs full of assay tables, drill logs and geology. The value is in
(a) honest retrieval over messy technical text, (b) pulling structured assay/depth/coordinate
data out of inconsistent tables, and (c) being able to *cite* exactly where an answer came from.

---

## Phase 0 — Setup ✅
- venv + RAG stack (sentence-transformers, faiss, pymupdf/pdfplumber, rank-bm25)
- project skeleton, config, git

## Phase 1 — Data acquisition ✅
- `src/ingest/fetch_metadata.py` queries the WAMEX spatial index (ArcGIS layer via SLIP) for the
  gold / Eastern-Goldfields slice -> data/raw/report_index.csv (30 reports: A-number, title, year,
  operator, commodity, abstract, centroid, details URL). 391 matched; capped to 30.
- Downloads: public path is a per-document signed URL (uploads.dmp.wa.gov.au/.../{anumber}?
  groupAccessToken=...). No clean A-number->URL pattern (tokens are server-issued), so PDFs are
  fetched manually by clicking "Download" on the ReportDetails page. Two reports in so far:
  A148715 (Kanowna Belle) + A148653 (Fimiston / Super Pit), both Northern Star.

## Phase 2 — Ingestion & text extraction ✅
- `src/ingest/extract_text.py` -> data/interim/pages.jsonl (one record/page with anumber+file+page
  provenance for citations). OCR-quality signals per page (alpha-ratio, word-likeness, image-only).
- Result on the 2 reports: 28 pages, 0% image-only (digital text layer), alpha-ratio 0.85.
  Found real intercepts in prose ("0.65 m at 0.09 g/t Au from 44.35 m"), drill IDs (FRGD00x).
  Detailed assay tables live in side-car ZIPs (later "fuse CSVs" enhancement).
- **Teaching note:** these are clean digital PDFs; we still want an older SCANNED report later to
  exercise real OCR-garbage handling (broken words, merged columns).

## Phase 3 — Chunking, embeddings & retrieval ✅
- `src/index/chunk.py`: page-bounded word chunks (size 350 / overlap 60) with chunk_id +
  anumber + page provenance. 543 pages -> 661 chunks.
- `src/index/build_index.py`: local embeddings (BAAI/bge-small-en-v1.5, 384-dim) -> FAISS
  inner-product (cosine) index. Persists chunks.jsonl + faiss.index.
- `src/index/retrieve.py`: HYBRID retrieval = semantic (FAISS) + lexical (BM25), fused with
  Reciprocal Rank Fusion. Demonstrated: semantic found "PBNC1322 ... 6 m @ 4.41 g/t Au from 45 m"
  by meaning; lexical nailed exact tenement IDs (P26/4224). Each hit tagged S / L / S+L.

## Phase 4 — Retrieval evaluation (the part most RAG demos skip) ✅
- `src/eval/questions.jsonl`: 18 labelled questions (intercepts, exact-ID lookups, project-name
  lookups, conceptual), each with a `verify` regex fingerprint of the answer. Label sanity-checked
  against the corpus.
- `src/eval/evaluate.py`: recall@k + MRR for semantic vs lexical vs hybrid (RRF).
  RESULT: MRR semantic 0.714 / lexical 0.817 / HYBRID 0.852; R@1 0.67 / 0.72 / 0.78.
- Findings: lexical is a strong baseline here (corpus facts are exact tokens — tenement IDs,
  drill-hole codes); semantic alone fumbles exact IDs (missed E15/2013, ranked Kanowna Lights 8th)
  but hybrid recovers them AND lifts fuzzy cases (PBND0226 4th/5th -> 1st). One honest miss: the
  conceptual "style of mineralisation at Binduli" — all methods missed in top-10 (answer buried on
  a conclusion page; query/phrasing mismatch) -> motivates query expansion / better chunking.

## Phase 5 — Structured extraction ✅
- `src/extract/intercepts.py`: regex extractor handling the corpus's format variants (@/at,
  g/t with/without space, decimal depths, from-to or single depth). Self-tested on known strings.
  -> data/processed/intercepts.csv: 699 intercepts from 12 reports (519 with hole id, 62 with
  depth interval — depths usually live in tables, not prose: an honest limitation).
- `src/extract/near.py`: joins intercepts to report centroids, haversine filter by distance +
  grade, dedupes cross-page restatements, returns rows WITH citations (A-number + page).
  Demo: 148 intercepts >=5 g/t within 30 km of Kalgoorlie, top 62.1 g/t [A138136 p54].
- Caveat: location granularity = report footprint centroid, not drill collar (collar coords need
  the drill CSVs). Extraction precision spot-checked OK; formal precision/recall vs the drill CSV
  is the rigorous follow-up.
- **Teaching note:** the "translate messy data into usable model inputs" requirement, literal.

## Phase 6 — Answer synthesis with citations (LLM, deferred)
- Compose answers from retrieved chunks with inline source citations (A-number + page).
- Faithfulness check: does the answer only claim what the cited chunks actually say?
- LLM is pluggable (local Ollama or an API key) — the hard parts above are provider-agnostic.

---

## Metrics we trust
- **recall@k / MRR** for retrieval (not "it gave an answer").
- **Extraction precision/recall** against a hand-checked sample of intercepts.
- **Faithfulness / citation accuracy** for generated answers — every claim traceable to a page.
