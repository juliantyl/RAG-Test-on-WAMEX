"""Phase 3c — hybrid retrieval: semantic (FAISS) + lexical (BM25), fused with RRF.

Why hybrid: embeddings capture meaning ("gold grade" ~ "Au mineralisation") but are weak on
EXACT tokens that matter here — tenement IDs (P26/4224), element symbols (Au), units (g/t),
drill-hole codes (FRGD001). BM25 nails those. Reciprocal Rank Fusion (RRF) combines the two
rankings without tuning score scales: an item ranked high by EITHER method floats up.

Usage:
  python -m src.index.retrieve "gold intercepts at Fimiston"
  from src.index.retrieve import Retriever; Retriever().search("...", k=8)
"""
from __future__ import annotations

import json
import re
import sys

import faiss
import numpy as np
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer

from src import config as C
from src.index.build_index import INDEX

CHUNKS = C.PROCESSED / "chunks.jsonl"
_TOKEN = re.compile(r"[A-Za-z0-9/.\-]+")


def _tok(s: str) -> list[str]:
    return _TOKEN.findall(s.lower())


class Retriever:
    def __init__(self):
        self.chunks = [json.loads(l) for l in CHUNKS.open(encoding="utf-8")]
        self.index = faiss.read_index(str(INDEX))
        self.model = SentenceTransformer(C.EMBED_MODEL)
        self.bm25 = BM25Okapi([_tok(c["text"]) for c in self.chunks])

    def _semantic_rank(self, query: str, n: int) -> list[int]:
        q = self.model.encode([query], normalize_embeddings=True).astype("float32")
        _, idx = self.index.search(q, n)
        return list(idx[0])

    def _lexical_rank(self, query: str, n: int) -> list[int]:
        scores = self.bm25.get_scores(_tok(query))
        return list(np.argsort(scores)[::-1][:n])

    def search(self, query: str, k: int = C.TOP_K, n: int = 50, rrf_k: int = 60):
        """Return top-k chunks by Reciprocal Rank Fusion of semantic + lexical rankings."""
        sem = self._semantic_rank(query, n)
        lex = self._lexical_rank(query, n)
        fused: dict[int, float] = {}
        for rank, i in enumerate(sem):
            fused[i] = fused.get(i, 0.0) + 1.0 / (rrf_k + rank)
        for rank, i in enumerate(lex):
            fused[i] = fused.get(i, 0.0) + 1.0 / (rrf_k + rank)
        top = sorted(fused, key=fused.get, reverse=True)[:k]
        return [{**self.chunks[i], "score": round(fused[i], 4),
                 "in_semantic": i in sem[:k], "in_lexical": i in lex[:k]} for i in top]


def main(argv: list[str]) -> None:
    query = " ".join(argv) or "gold intercepts at Fimiston"
    r = Retriever()
    print(f"Q: {query}\n")
    for hit in r.search(query):
        tag = "S+L" if hit["in_semantic"] and hit["in_lexical"] else ("S" if hit["in_semantic"] else "L")
        snippet = " ".join(hit["text"].split())[:200]
        print(f"[{hit['score']:.4f} {tag:3}] A{hit['anumber']} p{hit['page']}  {snippet}...")


if __name__ == "__main__":
    main(sys.argv[1:])
