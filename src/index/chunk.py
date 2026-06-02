"""Phase 3a — chunk page text into retrievable units, keeping provenance.

We chunk WITHIN a page (never across pages) so every chunk cites exactly one A-number+page.
Chunks are word-based with overlap so a fact split across a boundary still survives in one chunk.
Short pages become a single chunk; long pages split into overlapping windows.
"""
from __future__ import annotations

import json

from src import config as C

PAGES = C.INTERIM / "pages.jsonl"
CHUNKS = C.INTERIM / "chunks.jsonl"


def chunk_words(text: str, size: int, overlap: int) -> list[str]:
    words = text.split()
    if len(words) <= size:
        return [" ".join(words)] if words else []
    step = max(1, size - overlap)
    out = []
    for start in range(0, len(words), step):
        out.append(" ".join(words[start:start + size]))
        if start + size >= len(words):
            break
    return out


def build_chunks() -> list[dict]:
    pages = [json.loads(l) for l in PAGES.open(encoding="utf-8")]
    chunks = []
    for p in pages:
        if p["image_only"]:
            continue  # no usable text layer (would need OCR first)
        for j, piece in enumerate(chunk_words(p["text"], C.CHUNK_TOKENS, C.CHUNK_OVERLAP)):
            if len(piece.strip()) < 20:
                continue
            chunks.append({
                "chunk_id": f"A{p['anumber']}_p{p['page']}_{j}",
                "anumber": p["anumber"],
                "file": p["file"],
                "page": p["page"],
                "text": piece,
            })
    return chunks


def main() -> None:
    chunks = build_chunks()
    with CHUNKS.open("w", encoding="utf-8") as fh:
        for c in chunks:
            fh.write(json.dumps(c, ensure_ascii=False) + "\n")
    lengths = [len(c["text"].split()) for c in chunks]
    print(f"[ok] {len(chunks)} chunks -> {CHUNKS}")
    print(f"     words/chunk: min {min(lengths)}, median {sorted(lengths)[len(lengths)//2]}, max {max(lengths)}")


if __name__ == "__main__":
    main()
