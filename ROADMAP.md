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

## Phase 4 — Retrieval evaluation (the part most RAG demos skip)
- Build a small labelled eval set (questions -> which report/page truly answers them).
- Metrics: recall@k, MRR — "did the right source make it into the top-k?", not "did it answer".
- Compare semantic vs lexical vs hybrid; pick what actually works on this corpus.

## Phase 5 — Structured extraction
- Pull assay values (e.g. "3 m @ 5.2 g/t Au"), depths/intervals, and coordinates out of
  inconsistent text/tables into a clean schema (report, hole, from, to, grade, element, x, y).
- Enables the real query: "gold intercepts near these coordinates" via spatial filter + retrieval.
- **Teaching note:** this is the "translate messy data into usable model inputs" requirement, literal.

## Phase 6 — Answer synthesis with citations (LLM, deferred)
- Compose answers from retrieved chunks with inline source citations (A-number + page).
- Faithfulness check: does the answer only claim what the cited chunks actually say?
- LLM is pluggable (local Ollama or an API key) — the hard parts above are provider-agnostic.

---

## Metrics we trust
- **recall@k / MRR** for retrieval (not "it gave an answer").
- **Extraction precision/recall** against a hand-checked sample of intercepts.
- **Faithfulness / citation accuracy** for generated answers — every claim traceable to a page.
