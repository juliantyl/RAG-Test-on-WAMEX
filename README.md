# RAG over WAMEX Exploration Reports (gold, Eastern Goldfields)

A retrieval-augmented system over Western Australia's open-file mineral-exploration reports
(WAMEX): ingest a slice of the scanned, OCR'd PDFs and answer questions like *"what gold
intercepts were reported near these coordinates?"* with **cited sources**.

Focus is the genuinely hard parts of RAG on messy technical documents:
- chunking + local embeddings + **hybrid (semantic + lexical) retrieval**
- **retrieval evaluation** (recall@k / MRR), not just "it produced an answer"
- **structured extraction** of assays / depths / coordinates from inconsistent tables
- dealing with **OCR garbage** as a measured, first-class problem

See [ROADMAP.md](ROADMAP.md). Same region as Project 1 (the prospectivity model), so the two connect.

## Setup
```powershell
# Python 3.13, venv at .venv
.\.venv\Scripts\Activate.ps1
```
Stack (all local/free): sentence-transformers, faiss, pymupdf/pdfplumber, rank-bm25, scikit-learn.

## Layout
```
data/raw         downloaded WAMEX PDFs + metadata (gitignored)
data/interim     extracted page text, chunks
data/processed   embeddings index, extracted assay schema
src/config.py    paths, region, WAMEX endpoints, retrieval settings
src/ingest       acquisition + PDF text extraction + chunking
src/index        embeddings, vector store, retrieval
src/extract      structured assay/coord extraction
src/eval         retrieval evaluation (recall@k, MRR, faithfulness)
```
