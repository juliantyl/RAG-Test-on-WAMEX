"""Phase 3b — embed chunks and build the FAISS vector index.

Local embeddings (sentence-transformers, EMBED_MODEL) -> L2-normalised vectors -> FAISS
inner-product index (= cosine similarity). We persist the index + the chunk list so retrieval
can load them without re-embedding. BM25 (lexical) is cheap to rebuild at query time, so it's
not persisted here.

Run:  python -m src.index.build_index
"""
from __future__ import annotations

import json

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from src import config as C
from src.index.chunk import CHUNKS, build_chunks

INDEX = C.PROCESSED / "faiss.index"
CHUNKS_OUT = C.PROCESSED / "chunks.jsonl"


def main() -> None:
    chunks = build_chunks()
    # persist chunk list (the retrieval-time source of truth)
    with CHUNKS.open("w", encoding="utf-8") as fh, CHUNKS_OUT.open("w", encoding="utf-8") as fh2:
        for c in chunks:
            line = json.dumps(c, ensure_ascii=False) + "\n"
            fh.write(line); fh2.write(line)
    print(f"chunks: {len(chunks)}")

    print(f"loading embedder: {C.EMBED_MODEL} ...")
    model = SentenceTransformer(C.EMBED_MODEL)
    emb = model.encode([c["text"] for c in chunks], batch_size=64,
                       normalize_embeddings=True, show_progress_bar=True)
    emb = np.asarray(emb, dtype="float32")

    index = faiss.IndexFlatIP(emb.shape[1])   # cosine via normalised inner product
    index.add(emb)
    faiss.write_index(index, str(INDEX))
    print(f"[ok] FAISS index: {index.ntotal} vectors x {emb.shape[1]} dims -> {INDEX}")


if __name__ == "__main__":
    main()
