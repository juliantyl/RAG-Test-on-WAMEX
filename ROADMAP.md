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

## Phase 1 — Data acquisition
- Query the WAMEX spatial index (report footprints) for our Eastern Goldfields bbox.
- Download a tractable slice (~tens of reports) of public PDFs + their metadata (A-number,
  title, commodity, year, tenement, geometry). Keep raw PDFs in data/raw (gitignored).
- **Teaching note:** reports are huge and messy; we pick a focused slice so we spend effort on
  RAG, not on babysitting gigabytes.

## Phase 2 — Ingestion & text extraction
- Extract the existing OCR text layer per page (pymupdf); fall back to flagging image-only pages.
- Keep page-level provenance (report A-number + page number) on every piece of text — this is
  what makes citations possible later.
- **Teaching note:** confront OCR garbage head-on — broken words, merged columns, table soup.
  Measure how bad it is rather than pretending it's clean.

## Phase 3 — Chunking, embeddings & retrieval
- Chunking strategy for technical docs (size/overlap; respect page + section boundaries).
- Local embeddings (sentence-transformers) -> vector index (faiss).
- Hybrid retrieval: semantic (embeddings) + lexical (BM25) — lexical matters because assay codes,
  element symbols and tenement IDs are exact-match tokens embeddings handle poorly.

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
