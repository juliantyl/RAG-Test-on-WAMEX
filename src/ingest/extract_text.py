"""Phase 2 — extract per-page text from the downloaded report PDFs.

Scans data/raw/A<anumber>/ for *.pdf, pulls the text layer page-by-page with PyMuPDF, and
keeps PAGE-LEVEL PROVENANCE (anumber + file + page) on every record — that provenance is what
makes cited answers possible later. We also score each page's OCR quality instead of assuming
the text is clean: alpha-ratio + word-likeness flag garbled pages and image-only scans.

Output: data/interim/pages.jsonl  (one JSON object per page)
Run:    python -m src.ingest.extract_text
"""
from __future__ import annotations

import json
import re

import fitz  # PyMuPDF

from src import config as C

OUT = C.INTERIM / "pages.jsonl"
WORD_RE = re.compile(r"[A-Za-z]{2,}")


def ocr_quality(text: str) -> dict:
    """Cheap, honest readability signals for a page of (possibly OCR'd) text."""
    n_chars = len(text)
    stripped = text.replace(" ", "").replace("\n", "")
    n_alpha = sum(c.isalpha() for c in stripped)
    alpha_ratio = n_alpha / len(stripped) if stripped else 0.0
    tokens = text.split()
    wordlike = WORD_RE.findall(text)
    wordlike_ratio = len(wordlike) / len(tokens) if tokens else 0.0
    return {
        "n_chars": n_chars,
        "alpha_ratio": round(alpha_ratio, 3),       # low => symbol/garbage soup
        "wordlike_ratio": round(wordlike_ratio, 3), # low => broken tokens
        "image_only": n_chars < 50,                 # no real text layer -> needs OCR
    }


def extract_pdf(pdf_path, anumber: str):
    rows = []
    with fitz.open(pdf_path) as doc:
        for i, page in enumerate(doc, start=1):
            text = page.get_text("text")
            rows.append({
                "anumber": anumber,
                "file": pdf_path.name,
                "page": i,
                "text": text,
                **ocr_quality(text),
            })
    return rows


ANUM_RE = re.compile(r"[Aa](\d{5,6})")


def find_anumber(pdf_path) -> str | None:
    """Pull the WAMEX A-number from the filename or any parent folder name."""
    for part in (pdf_path.name, *[p.name for p in pdf_path.parents]):
        m = ANUM_RE.search(part)
        if m:
            return m.group(1)
    return None


def main() -> None:
    pdfs = sorted(C.RAW.glob("**/*.pdf"))   # any layout: flat files or A<num>/ folders
    if not pdfs:
        print(f"No PDFs found under {C.RAW} — download a report first.")
        return

    all_rows, seen, skipped = [], set(), []
    for pdf in pdfs:
        anumber = find_anumber(pdf)
        if anumber is None:
            skipped.append((pdf.name, "no A-number in name"))
            continue
        if anumber in seen:
            skipped.append((pdf.name, f"duplicate of A{anumber}"))
            continue
        seen.add(anumber)
        all_rows.extend(extract_pdf(pdf, anumber))
    n_reports = seen

    with OUT.open("w", encoding="utf-8") as fh:
        for r in all_rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    # summary
    n_pages = len(all_rows)
    img_only = sum(r["image_only"] for r in all_rows)
    mean_alpha = sum(r["alpha_ratio"] for r in all_rows) / n_pages
    mean_word = sum(r["wordlike_ratio"] for r in all_rows) / n_pages
    print(f"[ok] {len(n_reports)} unique report(s) -> {n_pages} pages")
    print(f"     image-only pages (need OCR): {img_only} ({img_only/n_pages*100:.0f}%)")
    print(f"     mean alpha-ratio {mean_alpha:.2f} | mean word-like ratio {mean_word:.2f}")
    print(f"     wrote {OUT}")
    if skipped:
        print(f"     skipped {len(skipped)} file(s):")
        for name, why in skipped:
            print(f"       - {name}  ({why})")


if __name__ == "__main__":
    main()
